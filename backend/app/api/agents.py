"""HTTP task API, with no model work in status/result reads."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from ..errors import ServiceError

MAX_SEQUENCE = (1 << 63) - 1

class CreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    requirements: str
    style: Literal['京剧写意', '国风幻想', '舞台角色'] = '京剧写意'
    parentTaskId: UUID | None = None

    @field_validator('requirements')
    @classmethod
    def valid_brief(cls, value):
        if not value or len(value.encode('utf-16-le')) // 2 > 1200 or any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('Invalid creation requirements')
        return value

class ConfirmRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirmationId: UUID
    expectedSequence: int = Field(ge=0, le=MAX_SEQUENCE, strict=True)
    action: Literal['accept']

class CancelRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expectedSequence: int = Field(ge=0, le=MAX_SEQUENCE, strict=True)

def register_agents(app, supervisor):
    router = APIRouter(prefix='/api/v1/agent')
    def status(task_id, request, after=0):
        return {**supervisor.store.status(task_id, after), 'requestId': request.state.request_id}

    @router.post('/create', status_code=202)
    async def create(data: CreateRequest, request: Request):
        key = request.headers.get('X-Idempotency-Key', '')
        if not 8 <= len(key) <= 128 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in key):
            raise ServiceError('INVALID_IDEMPOTENCY_KEY', '创作提交标识无效，请重新检查本次提交。', 400)
        task_id = supervisor.create(data.model_dump(mode='json', exclude_none=True), key)
        current = supervisor.store.status(task_id)
        return {'taskId': task_id, 'runId': task_id, 'state': current['state'], 'sequence': current['lastSequence'],
                'statusUrl': f'/api/v1/agent/status/{task_id}', 'resultUrl': f'/api/v1/agent/result/{task_id}',
                'requestId': request.state.request_id}

    @router.get('/status/{task_id}')
    async def task_status(task_id: str, request: Request, afterSequence: int = Query(default=0, ge=0, le=MAX_SEQUENCE)):
        return status(task_id, request, afterSequence)

    @router.get('/result/{task_id}')
    async def result(task_id: str, request: Request):
        return {**supervisor.store.result(task_id), 'requestId': request.state.request_id}

    @router.post('/confirm/{task_id}')
    async def confirm(task_id: str, data: ConfirmRequest, request: Request):
        supervisor.store.confirm(task_id, str(data.confirmationId), data.expectedSequence)
        return status(task_id, request)

    @router.post('/cancel/{task_id}')
    async def cancel(task_id: str, data: CancelRequest, request: Request):
        supervisor.store.cancel(task_id, data.expectedSequence)
        return status(task_id, request)

    app.include_router(router)
