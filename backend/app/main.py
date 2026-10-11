import asyncio
from collections import OrderedDict
from contextlib import asynccontextmanager
import hashlib
import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException
from .config import Settings
from .errors import ServiceError
from .schemas import QuestionRequest, SearchRequest, QuestionAnswer
from .services.runtime import Runtime
from .services.chat import grounded_answer
from .static_frontend import public_file
from .agents.supervisor import Supervisor
from .api.agents import register_agents

logger = logging.getLogger('xijing.requests')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

def create_app(settings=None):
    settings = settings or Settings()
    runtime = Runtime(settings)
    supervisor = Supervisor(runtime)
    runtime.agent_supervisor = supervisor
    @asynccontextmanager
    async def lifespan(app):
        try:
            await runtime.start()
            await supervisor.start()
            yield
        finally:
            try:
                await supervisor.close()
            finally:
                await runtime.close()
    app = FastAPI(title='戏境 AI', lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.runtime = runtime
    app.state.agent_supervisor = supervisor
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-Idempotency-Key'])
    cache, pending = OrderedDict(), {}

    @app.middleware('http')
    async def public_request(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        started = time.perf_counter()
        if request.method == 'POST':
            body = await request.body()
            if len(body) > 8192:
                error = ServiceError('BODY_TOO_LARGE', '请求内容过长，请缩短问题。', 413)
                response = JSONResponse(error.public(request.state.request_id), status_code=413)
            else:
                response = None
        else:
            response = None
        if response is None:
            try: response = await call_next(request)
            except Exception:
                response = JSONResponse(ServiceError('INTERNAL_ERROR', '服务出现内部错误，请稍后重试。', 500).public(request.state.request_id), status_code=500)
        response.headers['X-Request-ID'] = request.state.request_id
        logger.info('request_id=%s method=%s status=%s elapsed_ms=%.1f', request.state.request_id, request.method, response.status_code, (time.perf_counter()-started)*1000)
        return response

    @app.exception_handler(ServiceError)
    async def service_error(request, exc):
        return JSONResponse(exc.public(request.state.request_id), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        message = ('创作请求格式不正确：需求不能为空且最多1200个字符单位，风格与任务操作参数也须有效。'
                   if request.url.path.startswith('/api/v1/agent/') else
                   '请求格式不正确：问题不能为空且最多600个字符单位，请检查输入。')
        return JSONResponse(ServiceError('INVALID_REQUEST', message, 422).public(request.state.request_id), status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(ServiceError('NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR', '请求的公开资源不存在。' if exc.status_code == 404 else '请求无法处理。', exc.status_code).public(request.state.request_id), status_code=exc.status_code)

    @app.get('/api/v1/health')
    async def health(): return runtime.health()

    @app.get('/api/v1/capabilities')
    async def capabilities(): return runtime.capabilities()

    @app.post('/api/v1/knowledge/search')
    async def search(data: SearchRequest, request: Request):
        try:
            async with asyncio.timeout(settings.request_timeout_seconds):
                result = await runtime.knowledge(lambda: runtime.search_service.search(data.question, data.topK, data.category, settings.retrieval_mode))
        except TimeoutError:
            raise ServiceError('SEARCH_TIMEOUT', '检索超时，请稍后重试。', 504, True)
        return {**result, 'requestId': request.state.request_id}

    @app.get('/api/v1/knowledge/sources')
    async def sources():
        rows = await runtime.knowledge(runtime.store.sources if runtime.store else lambda: [])
        public_fields = {'source_id', 'title', 'category', 'author_or_organization', 'source_url', 'publication_date', 'collected_at', 'license_status', 'review_status', 'document_version', 'content_hash', 'content_kind', 'scope', 'license_url'}
        return {'sources': [{key: value for key, value in row.items() if key in public_fields} for row in rows]}

    @app.post('/api/v1/chat', response_model=QuestionAnswer)
    async def chat(data: QuestionRequest, request: Request):
        key = request.headers.get('X-Idempotency-Key')
        if key and (len(key) > 128 or not all(c.isalnum() or c in '-_' for c in key)):
            raise ServiceError('INVALID_IDEMPOTENCY_KEY', '请求标识格式不正确。', 400)
        signature = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
        now = time.monotonic()
        for old in list(cache):
            if now - cache[old][2] > 600: cache.pop(old)
        if key and key in cache:
            if cache[key][0] != signature: raise ServiceError('IDEMPOTENCY_CONFLICT', '同一请求标识不能用于不同问题。', 409)
            return cache[key][1]
        if key and key in pending:
            raise ServiceError('REQUEST_IN_PROGRESS', '该问题正在处理，请等待当前回答。', 409, True)
        if len(pending) >= 2: raise ServiceError('CHAT_BUSY', '问答正在处理其他请求，请稍后重试。', 429, True)
        slot = key or str(uuid.uuid4())
        pending[slot] = signature
        try:
            async with asyncio.timeout(settings.request_timeout_seconds):
                retrieval = await runtime.knowledge(lambda: runtime.search_service.search(data.question, settings.retrieval_top_k, None, settings.retrieval_mode))
                answer = await grounded_answer(data.question, retrieval, runtime.provider, request.state.request_id)
            if key:
                cache[key] = (signature, answer, time.monotonic())
                while len(cache) > 128: cache.popitem(last=False)
            return answer
        except TimeoutError:
            raise ServiceError('REQUEST_TIMEOUT', '本次问答超时，未自动重发模型请求；请稍后重试。', 504, True)
        finally: pending.pop(slot, None)

    register_agents(app, supervisor)

    @app.get('/{path:path}')
    async def frontend(path: str):
        if path == 'favicon.ico': return Response(status_code=204)
        return public_file(path)
    return app

app = create_app()
