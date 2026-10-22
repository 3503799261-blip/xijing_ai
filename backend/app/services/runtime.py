import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from datetime import datetime, timezone
import portalocker
from ..errors import ServiceError
from ..providers.llm import DeepSeekProvider

KNOWLEDGE_MESSAGES = {
    'KNOWLEDGE_NOT_INITIALIZED': '知识库尚未初始化，请按运行指南完成本地资料入库。',
    'KNOWLEDGE_LOCKED': '本地知识索引正由其他进程使用，请保留单个应用进程；不要删除锁文件。',
    'EMBEDDING_MODEL_MISSING': '缺少本地Embedding模型目录，请按运行指南恢复固定版本模型后重启。',
    'EMBEDDING_LOAD_FAILED': '本地Embedding模型加载失败，请检查模型文件完整性和固定版本后重启。',
    'KNOWLEDGE_DATABASE_MISSING': '缺少活动知识库SQLite文件，请恢复对应资料版本，或停止应用后按运行指南重新入库。',
    'KNOWLEDGE_DATABASE_UNAVAILABLE': '活动知识库SQLite无法读取，请检查资料版本和文件完整性后重启。',
    'VECTOR_INDEX_MISSING': '缺少活动Qdrant持久化索引，请恢复对应资料版本，或停止应用后按运行指南重新入库。',
    'VECTOR_INDEX_UNAVAILABLE': '活动Qdrant索引无法读取，请检查索引完整性和进程占用后重启。',
    'KNOWLEDGE_LOAD_FAILED': '知识索引版本或关联校验失败，请恢复配套的SQLite和Qdrant资料后重启。',
}

class Runtime:
    def __init__(self, settings):
        self.settings = settings
        self.provider = DeepSeekProvider(settings)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='opera-knowledge')
        self.search_service = None
        self.store = self.vectors = self.lock = None
        self.manifest = None
        self.diagnostic = 'KNOWLEDGE_NOT_INITIALIZED'
        self.inflight = 0

    def open(self):
        active = self.settings.rag_data_dir / 'active.json'
        if not active.exists():
            self.diagnostic = 'KNOWLEDGE_NOT_INITIALIZED'
            return
        stage = 'index'
        try:
            from ..knowledge.embedding import EmbeddingService
            from ..knowledge.store import KnowledgeStore
            from ..knowledge.vector_store import COLLECTION_NAME, VectorStore
            from .search import SearchService
            self.lock = portalocker.Lock(str(self.settings.rag_data_dir / 'index-owner.lock'), timeout=0)
            self.lock.acquire()
            self.manifest = json.loads(active.read_text(encoding='utf-8'))
            generation = self.manifest['generation_id']
            if not generation.startswith('gen-') or '/' in generation or '\\' in generation: raise ValueError('invalid generation')
            target = self.settings.rag_data_dir / 'generations' / generation
            # Serving must never turn a missing restored resource into an empty
            # database/collection. The separate ingestion path owns creation.
            for available, code in (
                (self.settings.embedding_model_path.is_dir(), 'EMBEDDING_MODEL_MISSING'),
                ((target / 'knowledge.sqlite3').is_file(), 'KNOWLEDGE_DATABASE_MISSING'),
                ((target / 'qdrant').is_dir() and (target / 'qdrant' / 'meta.json').is_file(), 'VECTOR_INDEX_MISSING'),
            ):
                if not available:
                    raise ServiceError(code, KNOWLEDGE_MESSAGES[code])
            try:
                vector_metadata = json.loads((target / 'qdrant' / 'meta.json').read_text(encoding='utf-8'))
                if not isinstance(vector_metadata, dict) or not isinstance(vector_metadata.get('collections'), dict):
                    raise ValueError('invalid local vector metadata')
            except (OSError, ValueError):
                raise ServiceError('VECTOR_INDEX_UNAVAILABLE', KNOWLEDGE_MESSAGES['VECTOR_INDEX_UNAVAILABLE']) from None
            # qdrant-client 1.19.1 local layout. An existing root/meta alone
            # still lets its constructor create a missing collection/storage.
            # This preflight is not a guarantee against concurrent file removal;
            # the application/build owner lock and controlled restore are required.
            if (not isinstance(vector_metadata['collections'].get(COLLECTION_NAME), dict)
                    or not (target / 'qdrant' / 'collection' / COLLECTION_NAME / 'storage.sqlite').is_file()):
                raise ServiceError('VECTOR_INDEX_MISSING', KNOWLEDGE_MESSAGES['VECTOR_INDEX_MISSING'])
            stage = 'embedding'
            embedding = EmbeddingService(self.settings.embedding_model_path)
            if embedding.model_revision != self.manifest['model_revision']: raise ValueError('Embedding revision mismatch')
            stage = 'knowledge'
            self.store = KnowledgeStore(target / 'knowledge.sqlite3')
            stage = 'vector'
            self.vectors = VectorStore(target / 'qdrant')
            stage = 'integrity'
            if self.store.count() != self.vectors.count(): raise ValueError('Index mismatch')
            self.vectors.validate_links(self.store.all_chunks())
            self.search_service = SearchService(embedding, self.store, self.vectors, self.settings.retrieval_min_score)
            self.diagnostic = None
        except Exception as exc:
            if isinstance(exc, portalocker.exceptions.LockException):
                self.diagnostic = 'KNOWLEDGE_LOCKED'
            elif isinstance(exc, ServiceError) and exc.code in KNOWLEDGE_MESSAGES:
                self.diagnostic = exc.code
            else:
                self.diagnostic = {'embedding': 'EMBEDDING_LOAD_FAILED', 'knowledge': 'KNOWLEDGE_DATABASE_UNAVAILABLE', 'vector': 'VECTOR_INDEX_UNAVAILABLE'}.get(stage, 'KNOWLEDGE_LOAD_FAILED')
            self.close_knowledge()

    def close_knowledge(self):
        self.search_service = None
        if self.vectors: self.vectors.close(); self.vectors = None
        if self.store: self.store.close(); self.store = None
        if self.lock: self.lock.release(); self.lock = None

    async def start(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self.open)

    async def close(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self.close_knowledge)
        self.executor.shutdown(wait=True)

    async def knowledge(self, function, *args):
        if not self.search_service:
            code = self.diagnostic or 'KNOWLEDGE_NOT_INITIALIZED'
            raise ServiceError(code, KNOWLEDGE_MESSAGES.get(code, KNOWLEDGE_MESSAGES['KNOWLEDGE_LOAD_FAILED']))
        if self.inflight >= 2:
            raise ServiceError('KNOWLEDGE_BUSY', '检索正在处理其他请求，请稍后重试。', 429, True)
        self.inflight += 1
        future = asyncio.get_running_loop().run_in_executor(self.executor, function, *args)
        future.add_done_callback(lambda _: setattr(self, 'inflight', self.inflight - 1))
        return await asyncio.shield(future)

    def capabilities(self):
        supervisor = getattr(self, 'agent_supervisor', None)
        assets = getattr(self, 'asset_service', None)
        models = assets.model_service if assets else None
        try:
            model_available = bool(models and models.available())
        except (ServiceError, OSError):
            model_available = False
        _, budget_ready = self.budget_status()
        return {'questionAnswering': bool(self.search_service and budget_ready and self.provider.verified), 'knowledgeSearch': bool(self.search_service), 'agentWorkflow': bool(supervisor and supervisor.available()), 'conceptImage': False, 'imageToModel': model_available, 'assetManagement': bool(assets), 'modelViewer': bool(assets), 'checkedAt': datetime.now(timezone.utc).isoformat()}

    def budget_status(self):
        try:
            if getattr(self.provider, 'database_error', None) is not None:
                raise self.provider.database_error
            return self.provider.ledger.summary(), True
        except (ServiceError, OSError, sqlite3.Error, AttributeError):
            return {'available': False, 'diagnostic': 'BUDGET_DATABASE_UNAVAILABLE',
                    'message': '模型预算数据库不可用，已停止付费调用；请检查配置并恢复原库。'}, False

    def health(self):
        supervisor = getattr(self, 'agent_supervisor', None)
        budget, budget_ready = self.budget_status()
        agents = supervisor.database_status() if supervisor else {'available': False, 'diagnostic': 'NOT_STARTED'}
        return {'status': 'ready' if self.capabilities()['questionAnswering'] and agents['available'] else 'degraded',
                'application': {'available': True},
                'databases': {'agent': agents, 'budget': {'available': budget_ready, 'diagnostic': None if budget_ready else 'BUDGET_DATABASE_UNAVAILABLE'}},
                'knowledge': bool(self.search_service), 'embedding': bool(self.search_service),
                'llmConfigured': self.provider.configured, 'llmVerified': bool(budget_ready and self.provider.verified),
                'diagnostic': self.diagnostic, 'documents': self.manifest.get('documents', 0) if self.manifest else 0,
                'chunks': self.manifest.get('chunks', 0) if self.manifest else 0, 'budget': budget,
                'agents': {'supervisorReady': bool(agents['available'] and supervisor and supervisor.ready and supervisor.worker and not supervisor.worker.done()),
                           'databaseAvailable': agents['available'], 'activeTaskId': supervisor.current_task if supervisor else None,
                           'enabled': self.settings.agent_workflow_enabled,
                           'diagnostic': agents.get('diagnostic') or (supervisor.diagnostic if supervisor else 'NOT_STARTED')}}
