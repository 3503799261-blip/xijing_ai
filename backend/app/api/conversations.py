"""Persisted local chat routes. No Agent task or model-creation operations."""
import asyncio
from fastapi import Query, Request, Response

from ..errors import ServiceError
from ..schemas import QuestionRequest
from ..services.chat import contextual_question, grounded_answer
from ..services.conversations import ConversationStore


# These errors happen before a generated answer / paid HTTP attempt or are
# documented rejected requests. All other post-admission failures are unknown.
SAFE_PROVIDER_FAILURES = {
    'LLM_KEY_MISSING', 'LLM_NOT_VERIFIED', 'LLM_OUTPUT_LIMIT',
    'LLM_BUSY', 'TEST_BUDGET_EXCEEDED', 'PHASE_BUDGET_EXCEEDED',
    'LLM_AUTH_FAILED', 'LLM_BALANCE', 'LLM_MODEL', 'LLM_PARAMETERS', 'LLM_RATE_LIMIT',
}


class TrackingProvider:
    def __init__(self, provider):
        self.provider = provider
        self.called = False

    async def generate(self, *args, **kwargs):
        # A budget DB error can also arise in ledger.finish after HTTP. Only
        # a failure positively observed here, before generate admission, is
        # safe to retry; a later same-code error remains an unknown outcome.
        database_error = getattr(self.provider, 'database_error', None)
        if database_error is not None:
            raise database_error
        summary = getattr(getattr(self.provider, 'ledger', None), 'summary', None)
        if callable(summary):
            summary()
        self.called = True
        return await self.provider.generate(*args, **kwargs)


def require_local_origin(request, settings):
    origin = request.headers.get('Origin')
    if origin is not None and origin not in settings.allowed_origins:
        raise ServiceError('FORBIDDEN_ORIGIN', '请从本机戏境AI页面进行对话操作。', 403)


def register_conversations(app, settings):
    store = ConversationStore(settings.rag_data_dir / 'chat-conversations')
    app.state.conversation_store = store

    @app.get('/api/v1/chat/conversations')
    def list_conversations(response: Response,
                           limit: int = Query(default=30, ge=1, le=50),
                           offset: int = Query(default=0, ge=0, le=100000)):
        response.headers['Cache-Control'] = 'no-store'
        return store.list(limit, offset)

    @app.post('/api/v1/chat/conversations', status_code=201)
    def create_conversation(request: Request, response: Response):
        require_local_origin(request, settings)
        response.headers['Cache-Control'] = 'no-store'
        return store.create()

    @app.get('/api/v1/chat/conversations/{identifier}')
    def read_conversation(identifier: str, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        return store.detail(identifier)

    return store


async def answer_conversation(data: QuestionRequest, request: Request, runtime, store, key):
    require_local_origin(request, runtime.settings)
    if (not key or not 8 <= len(key) <= 128
            or not all(c.isascii() and (c.isalnum() or c in '-_') for c in key)):
        raise ServiceError('INVALID_IDEMPOTENCY_KEY', '请重新发送这条消息，以生成有效请求标识。', 400)
    with store.locked(data.conversationId) as conversation:
        turn, reused = store.begin(conversation, data.question, key)
        if reused:
            return turn['answer']
        context = store.context(conversation, before_turn_id=turn['id'])
        provider = TrackingProvider(runtime.provider)
        try:
            async with asyncio.timeout(runtime.settings.request_timeout_seconds):
                query = contextual_question(data.question, context)
                retrieval = await runtime.knowledge(lambda: runtime.search_service.search(
                    query, runtime.settings.retrieval_top_k, None, runtime.settings.retrieval_mode))
                answer = await grounded_answer(data.question, retrieval, provider, request.state.request_id, context=context)
            store.finish(conversation, turn, answer=answer)
            return answer
        except TimeoutError:
            unknown = provider.called
            error = ServiceError('CHAT_OUTCOME_UNKNOWN' if unknown else 'REQUEST_TIMEOUT',
                                 '本次回答结果尚未确认，已阻止自动重复生成，请查看已保存记录。' if unknown else '检索暂时超时，请稍后手动重试。',
                                 504, not unknown)
            store.finish(conversation, turn, error=error.public('')['error'], unknown=unknown)
            raise error from None
        except ServiceError as error:
            unknown = provider.called and error.code not in SAFE_PROVIDER_FAILURES
            saved = error.public('')['error']
            if unknown:
                saved = {'code': error.code, 'message': error.message + ' 本次已停止，不会自动重复生成。', 'retryable': False}
            else:
                # A user may explicitly retry a pre-generation failure with
                # the same key; no retry is scheduled by this service.
                saved = {**saved, 'retryable': True}
            store.finish(conversation, turn, error=saved, unknown=unknown)
            if unknown:
                raise ServiceError(error.code, saved['message'], error.status, False) from None
            raise ServiceError(error.code, error.message, error.status, True) from None
        except BaseException:
            # Includes cancellation/disconnection. If saving fails, the prior
            # durable pending record still blocks future duplicate generation.
            error = {'code': 'CHAT_OUTCOME_UNKNOWN' if provider.called else 'CHAT_INTERRUPTED',
                     'message': '本次请求未完成，请查看已保存记录。', 'retryable': not provider.called}
            store.finish(conversation, turn, error=error, unknown=provider.called)
            raise
