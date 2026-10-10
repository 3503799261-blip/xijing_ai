import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timezone
import portalocker
from ..errors import ServiceError
from ..providers.llm import DeepSeekProvider

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
        if not active.exists(): return
        try:
            from ..knowledge.embedding import EmbeddingService
            from ..knowledge.store import KnowledgeStore
            from ..knowledge.vector_store import VectorStore
            from .search import SearchService
            self.lock = portalocker.Lock(str(self.settings.rag_data_dir / 'index-owner.lock'), timeout=0)
            self.lock.acquire()
            self.manifest = json.loads(active.read_text(encoding='utf-8'))
            generation = self.manifest['generation_id']
            if not generation.startswith('gen-') or '/' in generation or '\\' in generation: raise ValueError('invalid generation')
            target = self.settings.rag_data_dir / 'generations' / generation
            embedding = EmbeddingService(self.settings.embedding_model_path)
            if embedding.model_revision != self.manifest['model_revision']: raise ValueError('Embedding revision mismatch')
            self.store = KnowledgeStore(target / 'knowledge.sqlite3')
            self.vectors = VectorStore(target / 'qdrant')
            if self.store.count() != self.vectors.count(): raise ValueError('Index mismatch')
            self.vectors.validate_links(self.store.all_chunks())
            self.search_service = SearchService(embedding, self.store, self.vectors, self.settings.retrieval_min_score)
            self.diagnostic = None
        except Exception as exc:
            self.diagnostic = 'KNOWLEDGE_LOCKED' if isinstance(exc, portalocker.exceptions.LockException) else 'KNOWLEDGE_LOAD_FAILED'
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
            raise ServiceError(self.diagnostic or 'KNOWLEDGE_NOT_INITIALIZED', '知识库未就绪，请先完成入库；本地索引只能由一个应用进程持有。')
        if self.inflight >= 2:
            raise ServiceError('KNOWLEDGE_BUSY', '检索正在处理其他请求，请稍后重试。', 429, True)
        self.inflight += 1
        future = asyncio.get_running_loop().run_in_executor(self.executor, function, *args)
        future.add_done_callback(lambda _: setattr(self, 'inflight', self.inflight - 1))
        return await asyncio.shield(future)

    def capabilities(self):
        return {'questionAnswering': bool(self.search_service and self.provider.verified), 'knowledgeSearch': bool(self.search_service), 'agentWorkflow': False, 'conceptImage': False, 'imageToModel': False, 'checkedAt': datetime.now(timezone.utc).isoformat()}

    def health(self):
        return {'status': 'ready' if self.capabilities()['questionAnswering'] else 'degraded', 'knowledge': bool(self.search_service), 'embedding': bool(self.search_service), 'llmConfigured': self.provider.configured, 'llmVerified': self.provider.verified, 'diagnostic': self.diagnostic, 'documents': self.manifest.get('documents', 0) if self.manifest else 0, 'chunks': self.manifest.get('chunks', 0) if self.manifest else 0, 'budget': self.provider.ledger.summary()}
