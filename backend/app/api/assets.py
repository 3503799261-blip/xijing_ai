"""Bounded raw uploads and ID-only private asset serving."""
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from starlette.concurrency import run_in_threadpool
from ..errors import ServiceError
from ..assets.schemas import CreateAsset, VisualApproval, ImageAcceptance, ModelApprovalRequest, ModelSubmitRequest, PromptVersionRequest
from ..assets.validation import MAX_IMAGE_BYTES, MAX_MODEL_BYTES
from ..assets.candidates import CandidateCatalog
from ..assets.candidate_preview import candidate_preview
from ..assets.internal_viewer import internal_viewer


def require_local_internal_access(request):
    """Private technical artifacts are accessible only from this local machine."""
    if (not request.client or request.client.host not in ('127.0.0.1', '::1')
            or request.url.hostname not in ('127.0.0.1', 'localhost', '::1')
            or request.headers.get('sec-fetch-site') == 'cross-site'):
        raise ServiceError('ASSET_FILE_NOT_FOUND', '该资源不对外公开。', 404)


def protect_internal_model(item, request):
    if item.get('internalUseOnly') is True or item.get('visibility') == 'internal':
        require_local_internal_access(request)


async def bounded_body(request, limit):
    length = request.headers.get('content-length')
    if length is not None:
        try:
            declared = int(length)
        except ValueError:
            raise ServiceError('BODY_LENGTH_INVALID', '上传长度声明无效。', 400)
        if declared < 0 or declared > limit:
            raise ServiceError('BODY_TOO_LARGE', '上传文件超过允许大小。', 413)
    data = bytearray()
    async for block in request.stream():
        if len(data) + len(block) > limit:
            raise ServiceError('BODY_TOO_LARGE', '上传文件超过允许大小。', 413)
        data.extend(block)
    if not data:
        raise ServiceError('EMPTY_ASSET_FILE', '请上传实际文件，不能提交空内容。', 422)
    return bytes(data)


def register_assets(app, service):
    router = APIRouter(prefix='/api/v1/assets')
    candidates = CandidateCatalog(service)
    def response(value, request):
        return {**value, 'requestId': getattr(request.state, 'request_id', None)}

    # Read-only review material is separate from character images and approvals.
    # There is deliberately no browser registration/acceptance/model route here.
    @router.get('/candidates/{candidate_id}')
    async def candidate(candidate_id: str, request: Request):
        return response(await run_in_threadpool(candidates.get, candidate_id), request)

    @router.get('/candidates/{candidate_id}/file')
    async def candidate_file(candidate_id: str):
        path = await run_in_threadpool(candidates.file_path, candidate_id)
        item = await run_in_threadpool(candidates.get, candidate_id)
        return FileResponse(path, media_type='image/png', headers={
            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
            'ETag': '"' + item['hash'] + '"'})

    @router.get('/candidates/{candidate_id}/preview', response_class=HTMLResponse)
    async def preview_candidate(candidate_id: str):
        item = await run_in_threadpool(candidates.get, candidate_id)
        return HTMLResponse(candidate_preview(item), headers={
            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'none'; script-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"})

    @router.post('/characters', status_code=201)
    async def create(data: CreateAsset, request: Request):
        return response(service.create_character(data), request)

    @router.get('/characters')
    async def characters(request: Request, characterId: str | None = None, sourceTaskId: str | None = None,
                         mode: str | None = Query(default=None, pattern=r'^(personal|enterprise)$')):
        return response({'characters': service.list_characters(characterId, sourceTaskId, mode)}, request)

    @router.get('/characters/{asset_id}')
    async def character(asset_id: str, request: Request):
        return response(service.get_character(asset_id), request)

    @router.get('/characters/{asset_id}/styles')
    async def character_styles(asset_id: str, request: Request):
        return response(service.list_styles(asset_id), request)

    @router.post('/characters/{asset_id}/prompt-versions', status_code=201)
    async def prompt_version(asset_id: str, data: PromptVersionRequest, request: Request):
        return response(service.create_prompt_version(asset_id, data), request)

    @router.post('/characters/{asset_id}/visual-approval')
    async def visual_approval(asset_id: str, data: VisualApproval, request: Request):
        return response(service.approve_visual(asset_id, data.promptHash), request)

    @router.post('/images', status_code=201)
    async def image_upload(request: Request, assetId: str = Query(min_length=36, max_length=36),
                           provenance: str = Query(pattern=r'^(manual_image|imported_ai_image)$'),
                           licenseNote: str = Query(min_length=1, max_length=1000)):
        raw = await bounded_body(request, MAX_IMAGE_BYTES)
        mime = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        return response(await run_in_threadpool(service.upload_image, assetId, raw, mime, provenance, licenseNote), request)

    @router.get('/images/{image_id}')
    async def image(image_id: str, request: Request):
        return response(service.get_image(image_id), request)

    @router.get('/images/{image_id}/file')
    async def image_file(image_id: str):
        return FileResponse(await run_in_threadpool(service.file_path, 'image', image_id), media_type='image/png',
                            headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, max-age=3600'})

    @router.post('/images/{image_id}/accept')
    async def image_accept(image_id: str, data: ImageAcceptance, request: Request):
        return response(service.accept_image(image_id, data.imageHash), request)

    @router.post('/models/import', status_code=201)
    async def model_import(request: Request, assetId: str = Query(min_length=36, max_length=36),
                           licenseNote: str = Query(min_length=1, max_length=1000)):
        mime = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if mime not in ('model/gltf-binary', 'application/octet-stream'):
            raise ServiceError('MODEL_FORMAT_INVALID', '请以GLB二进制文件上传。', 415)
        raw = await bounded_body(request, MAX_MODEL_BYTES)
        return response(await run_in_threadpool(service.import_model, assetId, raw, licenseNote), request)

    @router.get('/models')
    async def models(request: Request, http_response: Response, assetId: str | None = None,
                     includeInternal: bool = False):
        # The local workbench may discover an existing private technical model,
        # without changing its identity or making it a public character asset.
        # Ordinary callers retain the original public-list behaviour.
        if includeInternal:
            require_local_internal_access(request)
            http_response.headers['Cache-Control'] = 'private, no-store'
            values = service.list_models(assetId, include_internal=True)
        else:
            values = service.list_models(assetId)
        result = {'models': values}
        if includeInternal:
            result['internalIncluded'] = True
        return response(result, request)

    @router.get('/models/{model_id}')
    async def model(model_id: str, request: Request):
        item = service.get_model(model_id)
        protect_internal_model(item, request)
        return response(item, request)

    @router.get('/models/{model_id}/file')
    async def model_file(model_id: str, request: Request):
        item = service.get_model(model_id)
        protect_internal_model(item, request)
        return FileResponse(await run_in_threadpool(service.file_path, 'model', model_id), media_type='model/gltf-binary',
                            headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, no-store' if item.get('internalUseOnly') else 'private, max-age=3600',
                                     'ETag': '"' + item['hash'] + '"'})

    @router.get('/models/{model_id}/download')
    async def model_download(model_id: str, request: Request):
        item = service.get_model(model_id)
        protect_internal_model(item, request)
        return FileResponse(await run_in_threadpool(service.file_path, 'model', model_id), media_type='model/gltf-binary',
                            filename=f"xijing-{item['modelId']}.glb", headers={'X-Content-Type-Options': 'nosniff'})

    @router.get('/internal-models/{model_id}/viewer', response_class=HTMLResponse)
    async def technical_viewer(model_id: str, request: Request):
        require_local_internal_access(request)
        item = service.get_model(model_id)
        if item.get('origin') != 'neural4d_technical_test' or item.get('internalUseOnly') is not True:
            raise ServiceError('ASSET_FILE_NOT_FOUND', '未找到内部技术验证模型。', 404)
        return HTMLResponse(internal_viewer(item), headers={'Cache-Control': 'private, no-store',
            'X-Content-Type-Options': 'nosniff',
            # The pinned local model-viewer bundle initializes a Wasm decoder.
            # Permit only Wasm compilation; string-JS eval and remote script or
            # resource origins stay blocked by this internal page's CSP.
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' blob:; worker-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'"})

    @router.get('/usage')
    async def usage(request: Request):
        return response(service.usage_summary(), request)

    @router.post('/neural4d/verify')
    async def verify(request: Request):
        data = await request.json()
        if data != {'action': 'verify_balance'}:
            raise ServiceError('INVALID_REQUEST', '必须明确请求只读余额验证。', 422)
        model_service = service.require_model_service()
        model_service.authorize(request.headers.get('X-Asset-Admin-Token'))
        return response(await model_service.verify(), request)

    @router.post('/model-approvals')
    async def model_approval(data: ModelApprovalRequest, request: Request):
        model_service = service.require_model_service()
        model_service.authorize(request.headers.get('X-Asset-Admin-Token'))
        return response(model_service.approve(data.model_dump()), request)

    @router.post('/model-tasks', status_code=202)
    async def model_submit(data: ModelSubmitRequest, request: Request):
        key = request.headers.get('X-Idempotency-Key', '')
        if not 8 <= len(key) <= 128 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in key):
            raise ServiceError('INVALID_IDEMPOTENCY_KEY', '建模提交标识无效。', 400)
        model_service = service.require_model_service()
        model_service.authorize(request.headers.get('X-Asset-Admin-Token'))
        return response(await model_service.submit(data.model_dump(), key), request)

    @router.get('/model-tasks/{job_id}')
    async def model_status(job_id: str, request: Request):
        return response(service.require_model_service().status(job_id), request)

    @router.post('/model-tasks/{job_id}/refresh')
    async def model_refresh(job_id: str, request: Request):
        model_service = service.require_model_service()
        model_service.authorize(request.headers.get('X-Asset-Admin-Token'))
        return response(await model_service.refresh(job_id), request)

    @router.post('/model-tasks/{job_id}/query-continuation')
    async def continue_queries(job_id: str, request: Request):
        if await request.json() != {'action': 'accept_query_continuation'}:
            raise ServiceError('INVALID_REQUEST', '请明确确认继续查询原任务。', 422)
        model_service = service.require_model_service()
        model_service.authorize(request.headers.get('X-Asset-Admin-Token'))
        return response(model_service.continue_queries(job_id), request)

    app.include_router(router)
