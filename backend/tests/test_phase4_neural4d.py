"""OFFLINE integration only: explicit httpx.MockTransport, temporary SQLite.

No runtime/project ledger, provider DNS, credentials or paid/model APIs are used.
The synthetic responses below are contract fixtures, not Neural4D evidence.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import socket
from threading import Barrier
import time
from types import SimpleNamespace

import httpx
from pydantic import SecretStr
import pytest

from backend.app.agents.store import TaskStore
from backend.app.assets.neural_service import ModelService
from backend.app.assets.service import AssetService
from backend.app.assets.usage import UsageManager
from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.providers.neural4d import Neural4DProvider, PARAMETERS, parameters_for_style
from backend.tests.test_phase4_assets import asset, image_bytes, glb, api

FAKE_KEY = 'offline-mock-not-a-real-provider-key'
FAKE_ADMIN = 'offline-local-admin-token-test-only'
DOWNLOAD_HOST = 'assets.example.invalid'


@pytest.fixture(autouse=True)
def no_dns(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline integration attempted real DNS/network.')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.fixture
def setup(tmp_path):
    services = []
    def create(handler=None, *, enabled=False, protocol=False, history=0, key=FAKE_KEY):
        directory = tmp_path / f'integration-{len(services)}'
        settings = Settings(_env_file=None, rag_data_dir=directory / 'runtime', embedding_model_path=directory / 'unused-model',
                            deepseek_api_key=SecretStr(''), neural4d_api_key=SecretStr(key),
                            neural4d_admin_token=SecretStr(FAKE_ADMIN), neural4d_generation_enabled=enabled,
                            neural4d_protocol_verified=protocol, neural4d_expected_credits=80,
                            neural4d_download_hosts=[DOWNLOAD_HOST])
        calls = []
        def default(request):
            calls.append(request)
            if request.url.path.endswith('queryPointsInfo'):
                return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
            number = sum(r.url.path.endswith('generateModelWithImage') for r in calls)
            return httpx.Response(200, json={'uuid': f'offline-model-uuid-{number}'})
        transport = httpx.MockTransport(handler or default)
        directory.mkdir(parents=True)
        tasks = TaskStore(directory / 'tasks.sqlite3')
        assets = AssetService(settings, tasks)
        usage = UsageManager(directory / 'private-offline-quota.sqlite3')
        if history is not None:
            usage.initialize_history(history, '仅离线模拟：不是实际项目历史或账户余额。')
        models = ModelService(settings, assets, usage, transport)
        services.append(models)
        models.start()
        assets.usage, assets.model_service = usage, models
        return SimpleNamespace(settings=settings, tasks=tasks, assets=assets, usage=usage,
                               models=models, provider=models.provider, calls=calls, transport=transport)
    yield create
    for service in reversed(services):
        service.close()


def prepared(context, *, style_mode='realistic', source_task_id=None, purpose='仅离线测试'):
    if source_task_id is None:
        created = asset(context.assets, context.tasks, styleMode=style_mode, purpose=purpose)
    else:
        created = context.assets.create_character({'sourceTaskId': source_task_id, 'styleMode': style_mode,
                                                   'purpose': purpose, 'mode': 'personal'})
    context.assets.approve_visual(created['assetId'], created['visualPrompt']['promptHash'])
    image = context.assets.upload_image(created['assetId'], image_bytes(), 'image/png', 'manual_image', '仅离线原创图片测试')
    image = context.assets.accept_image(image['imageId'], image['hash'])
    return {'assetId': created['assetId'], 'assetVersion': created['version'], 'imageId': image['imageId'],
            'imageHash': image['hash'], 'promptHash': created['visualPrompt']['promptHash'],
            'characterId': created['characterId'], 'styleMode': created['styleMode'], 'styleVersion': created['styleVersion'],
            'purpose': created['purpose'], 'modelCount': 1, 'estimatedCredits': 80, 'action': 'accept'}


def approve(context, data):
    asyncio.run(context.models.verify())
    return context.models.approve(data)


def test_api_authorization_and_generation_default_off_emit_no_provider_requests(setup):
    context = setup()
    data = prepared(context)
    client = api(context.assets)
    assert client.post('/api/v1/assets/model-approvals', json=data).status_code == 403
    assert client.post('/api/v1/assets/model-approvals', json=data,
                       headers={'X-Asset-Admin-Token': FAKE_ADMIN}).status_code == 403
    with pytest.raises(ServiceError, match='NEURAL4D_PROTOCOL_UNVERIFIED'):
        asyncio.run(context.models.verify())
    assert context.calls == [] and context.usage.summary()['occupied_attempts'] == 0


def test_configured_key_does_not_replace_verification_history_or_approval(setup):
    context = setup(enabled=True, protocol=True, history=None)
    data = prepared(context)
    asyncio.run(context.models.verify())
    with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
        context.models.approve(data)
    assert len(context.calls) == 1
    assert context.calls[0].url.path.endswith('queryPointsInfo')
    assert context.usage.summary()['remaining_attempts'] is None


def test_missing_key_never_reaches_transport_even_when_protocol_enabled(setup):
    context = setup(enabled=True, protocol=True, key='')
    with pytest.raises(ServiceError, match='NEURAL4D_KEY_MISSING'):
        asyncio.run(context.models.verify())
    assert context.calls == [] and context.usage.summary()['occupied_attempts'] == 0


def test_successful_creation_multipart_fixed_single_model_and_local_replay(setup, caplog):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-key-0001'))
    repeated = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-key-0001'))
    create_calls = [r for r in context.calls if r.url.path.endswith('generateModelWithImage')]
    assert len(create_calls) == 1
    request = create_calls[0]
    assert request.method == 'POST' and request.headers['content-type'].startswith('multipart/form-data; boundary=')
    assert request.headers['authorization'] == 'Bearer ' + FAKE_KEY
    body = request.content
    assert body.count(b'name="modelCount"') == 1
    assert b'name="modelCount"\r\n\r\n1\r\n' in body
    assert b'name="image"; filename="concept.png"' in body and b'\x89PNG' in body
    assert submitted['state'] == 'SUBMITTED' and submitted['attemptId'] == repeated['attemptId']
    assert context.usage.summary()['occupied_attempts'] == 1
    assert context.usage.summary()['realHttpRequests'] == 0 and context.usage.summary()['mockHttpRequests'] == 2
    assert FAKE_KEY not in caplog.text and FAKE_KEY not in json.dumps(submitted)


def test_provider_rejects_changed_image_before_claiming_or_sending(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    attempt = context.usage.reserve('offline-direct-claim', confirmation['approvalId'], payload, data['purpose'], True, True)
    with pytest.raises(ServiceError, match='NEURAL4D_INPUT_CHANGED'):
        asyncio.run(context.provider.create_once(attempt['attemptId'], b'changed-image'))
    assert len(context.calls) == 1
    assert context.usage.get_attempt(attempt['attemptId'])['state'] == 'RESERVED'


@pytest.mark.parametrize('mutate', ['purpose', 'source', 'image', 'prompt'])
def test_frozen_approval_rechecks_authoritative_asset_drift_before_creation(setup, mutate):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    stored = context.assets.store.get(data['assetId'])
    if mutate == 'purpose':
        stored['purpose'] = '不同用途'
    elif mutate == 'source':
        stored['sourceResultHash'] = 'f' * 64
    elif mutate == 'prompt':
        stored['visualPrompt']['promptHash'] = 'e' * 64
    else:
        image = context.assets.store.file('image', data['imageId'])
        image['accepted'] = False
        with context.assets.store.connect() as db:
            db.execute('UPDATE asset_images SET content_json=? WHERE image_id=?', (json.dumps(image), data['imageId']))
    if mutate != 'image':
        with context.assets.store.connect() as db:
            db.execute('UPDATE character_assets SET content_json=? WHERE asset_id=?', (json.dumps(stored), data['assetId']))
    with pytest.raises(ServiceError, match='NEURAL4D_INPUT_CHANGED'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-drift-key'))
    assert len(context.calls) == 1 and context.usage.summary()['occupied_attempts'] == 0


def test_changed_authoritative_phase3_result_invalidates_frozen_asset(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    character = context.assets.get_character(data['assetId'])
    task_id = character['sourceTaskId']
    result = context.tasks.result(task_id)
    result['design']['name'] = '被修改的离线角色'
    with context.tasks.connect() as db:
        db.execute('UPDATE agent_tasks SET result_json=? WHERE task_id=?', (json.dumps(result), task_id))
    with pytest.raises(ServiceError, match='NEURAL4D_INPUT_CHANGED'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-source-drift'))
    assert len(context.calls) == 1 and context.usage.summary()['occupied_attempts'] == 0


def test_concurrent_same_attempt_creates_only_one_http_request(setup):
    calls = []
    async def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        await asyncio.sleep(0.03)
        return httpx.Response(200, json={'uuid': 'offline-race-uuid'})
    context = setup(handler, enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    async def race():
        request = {'approvalId': confirmation['approvalId'], 'modelCount': 1}
        return await asyncio.gather(context.models.submit(request, 'offline-race-key'),
                                    context.models.submit(request, 'offline-race-key'), return_exceptions=True)
    results = asyncio.run(race())
    assert not any(isinstance(r, Exception) for r in results)
    assert results[0]['attemptId'] == results[1]['attemptId']
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    assert context.usage.summary()['occupied_attempts'] == 1


@pytest.mark.parametrize('failure', ['timeout', 'http_500', 'http_408', 'invalid_json', 'list_json'])
def test_uncertain_create_preserves_quota_and_blocks_recreation(setup, failure):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if failure == 'timeout':
            raise httpx.ReadTimeout('offline timeout fixture', request=request)
        if failure == 'invalid_json':
            return httpx.Response(200, content=b'<invalid>')
        if failure == 'list_json':
            return httpx.Response(200, json=['not-a-task-object'])
        return httpx.Response(int(failure[-3:]), json={'offline': 'failure'})
    context = setup(handler, enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    with pytest.raises(ServiceError):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-unknown-key'))
    attempt = next(iter(context.usage.summary()['attemptStates']))
    assert attempt == 'UNKNOWN'
    assert context.usage.summary()['occupied_attempts'] == 1 and context.usage.summary()['remaining_attempts'] == 2
    assert context.models.available() is False
    assert context.usage.summary()['creationPaused'] is True
    with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
        context.models.approve(data)
    replay = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-unknown-key'))
    assert replay['state'] == 'UNKNOWN'  # Readback is allowed, never another send.
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1


@pytest.mark.parametrize('unknown_state', ['UNKNOWN', 'PENDING_RECONCILIATION'])
def test_global_pause_blocks_other_style_but_allows_original_query_and_replay(setup, unknown_state):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-paused-original'})
        assert request.url.path.endswith('retrieveModel')
        assert json.loads(request.content) == {'uuid': 'offline-paused-original'}
        return httpx.Response(200, json={'codeStatus': 1})

    context = setup(handler, enabled=True, protocol=True)
    chibi = prepared(context, style_mode='chibi', purpose='离线Q版首个任务')
    source_task_id = context.assets.get_character(chibi['assetId'])['sourceTaskId']
    realistic = prepared(context, style_mode='realistic', source_task_id=source_task_id, purpose='离线写实另一个用途')
    first = approve(context, chibi)
    future = context.models.approve(realistic)
    original_request = {'approvalId': first['approvalId'], 'modelCount': 1}
    sent = asyncio.run(context.models.submit(original_request, 'offline-paused-original'))
    context.usage.finish(sent['jobId'], unknown_state, error_code='OFFLINE_UNKNOWN_AFTER_SEND')

    assert context.models.available() is False
    assert context.assets.usage_summary()['realEnabled'] is False
    assert context.assets.usage_summary()['pauseCode'] == 'NEURAL4D_RECONCILIATION_REQUIRED'
    with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
        context.models.approve(realistic)
    with pytest.raises(ServiceError, match='NEURAL4D_RECONCILIATION_REQUIRED'):
        asyncio.run(context.models.submit({'approvalId': future['approvalId'], 'modelCount': 1}, 'offline-other-style'))
    replay = asyncio.run(context.models.submit(original_request, 'offline-paused-original'))
    assert replay['jobId'] == sent['jobId'] and replay['state'] == unknown_state
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    assert context.usage.summary()['occupied_attempts'] == 1

    # Only a deliberate query of the known original UUID resolves its state.
    # This query never schedules or sends the separately approved style.
    reconciled = asyncio.run(context.models.refresh(sent['jobId']))
    assert reconciled['state'] == 'PROCESSING'
    assert context.usage.summary()['creationPaused'] is False
    assert context.models.available() is True
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    assert sum(r.url.path.endswith('retrieveModel') for r in calls) == 1
    assert context.usage.summary()['realHttpRequests'] == 0


def test_provider_cannot_send_already_reserved_other_style_after_unknown(setup):
    context = setup(enabled=True, protocol=True)
    chibi = prepared(context, style_mode='chibi', purpose='离线首个任务')
    realistic = prepared(context, style_mode='realistic', purpose='离线已预约任务')
    first = approve(context, chibi)
    second = context.models.approve(realistic)
    first_payload = context.models.approval_payload(first['approvalId'])
    first_attempt = context.usage.reserve('offline-claim-first', first['approvalId'], first_payload, chibi['purpose'], True, True)
    second_payload = context.models.approval_payload(second['approvalId'])
    waiting = context.usage.reserve('offline-claim-waiting', second['approvalId'], second_payload, realistic['purpose'], True, True)
    context.usage.mark_started(first_attempt['attemptId'])
    context.usage.finish(first_attempt['attemptId'], 'UNKNOWN', error_code='OFFLINE_UNKNOWN')
    raw = context.assets.file_path('image', realistic['imageId']).read_bytes()
    with pytest.raises(ServiceError, match='NEURAL4D_RECONCILIATION_REQUIRED'):
        asyncio.run(context.provider.create_once(waiting['attemptId'], raw))
    assert context.usage.get_attempt(waiting['attemptId'])['state'] == 'RESERVED'
    assert context.usage.get_attempt(waiting['attemptId'])['startedAt'] is None
    assert context.usage.summary()['occupied_attempts'] == 2
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_multiple_returned_models_halt_future_creations_even_with_new_input(setup):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        return httpx.Response(200, json={'uuids': ['offline-1', 'offline-2']})
    context = setup(handler, enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    with pytest.raises(ServiceError, match='NEURAL4D_RESPONSE_INVALID'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-multiple-ids'))
    assert context.usage.summary()['creationHalted']
    with pytest.raises(ServiceError):
        next_data = prepared(context)
        next_confirmation = context.models.approve(next_data)
        asyncio.run(context.models.submit({'approvalId': next_confirmation['approvalId'], 'modelCount': 1}, 'offline-halt-next'))
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1


def test_direct_provider_cannot_send_same_claim_twice(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    attempt = context.usage.reserve('offline-provider-only', confirmation['approvalId'], payload, data['purpose'], True, True)
    raw = context.assets.file_path('image', data['imageId']).read_bytes()
    asyncio.run(context.provider.create_once(attempt['attemptId'], raw))
    with pytest.raises(ServiceError, match='NEURAL4D_ATTEMPT_ALREADY_STARTED'):
        asyncio.run(context.provider.create_once(attempt['attemptId'], raw))
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1


def test_owner_lock_blocks_second_worker_and_startup_recovery_never_resends(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    attempt = context.usage.reserve('offline-orphan-claim', confirmation['approvalId'], payload, data['purpose'], True, True)
    second = ModelService(context.settings, context.assets, UsageManager(context.usage.path), context.transport)
    try:
        second.start()
        assert second.owner is None and not second.available()
        assert context.usage.get_attempt(attempt['attemptId'])['state'] == 'RESERVED'
        context.models.close()
        second.start()
        assert second.owner is not None
        assert context.usage.get_attempt(attempt['attemptId'])['state'] == 'PENDING_RECONCILIATION'
        with pytest.raises(ServiceError, match='NEURAL4D_ATTEMPT_ALREADY_STARTED'):
            asyncio.run(second.provider.create_once(attempt['attemptId'], context.assets.file_path('image', data['imageId']).read_bytes()))
        assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0
    finally:
        second.close()


def test_signed_download_never_forwards_authorization_or_follows_redirect(setup):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path == '/redirect.glb':
            return httpx.Response(302, headers={'Location': 'https://evil.example.invalid/new.glb'})
        return httpx.Response(200, content=glb())
    context = setup(handler)
    result = asyncio.run(context.provider.download(f'https://{DOWNLOAD_HOST}/model.glb?signature=offline-signature'))
    assert result.startswith(b'glTF') and 'authorization' not in requests[0].headers
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(context.provider.download(f'https://{DOWNLOAD_HOST}/redirect.glb'))
    assert len(requests) == 2
    for url in ('http://127.0.0.1/model.glb', 'https://evil.example.invalid/model.glb',
                f'https://name:password@{DOWNLOAD_HOST}/model.glb', f'https://{DOWNLOAD_HOST}:444/model.glb'):
        with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
            asyncio.run(context.provider.download(url))
    assert len(requests) == 2
    with context.usage.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM neural4d_operational_requests')]
    assert 'offline-signature' not in json.dumps(rows) and FAKE_KEY not in json.dumps(rows)


@pytest.mark.parametrize('kind', ['http_404', 'timeout'])
def test_failed_download_is_recorded_without_signed_url_or_secret(setup, kind):
    def handler(request):
        if kind == 'timeout':
            raise httpx.ReadTimeout('offline fixture', request=request)
        return httpx.Response(404, content=b'offline missing file')
    context = setup(handler)
    with pytest.raises(ServiceError):
        asyncio.run(context.provider.download(f'https://{DOWNLOAD_HOST}/missing.glb?signature=offline-private-query'))
    with context.usage.connect() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM neural4d_operational_requests WHERE operation='download'")]
    assert len(rows) == 1
    assert rows[0]['error_code'] and rows[0]['is_mock'] == 1
    assert 'offline-private-query' not in json.dumps(rows) and FAKE_KEY not in json.dumps(rows)
    assert context.usage.summary()['occupied_attempts'] == 0


def test_last_slot_submission_replay_returns_original_even_when_quota_exhausted(setup):
    context = setup(enabled=True, protocol=True, history=2)
    data = prepared(context)
    confirmation = approve(context, data)
    request = {'approvalId': confirmation['approvalId'], 'modelCount': 1}
    first = asyncio.run(context.models.submit(request, 'offline-last-slot'))
    assert context.usage.summary()['remaining_attempts'] == 0
    replay = asyncio.run(context.models.submit(request, 'offline-last-slot'))
    assert replay['attemptId'] == first['attemptId']
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1


def test_received_uuid_but_failed_local_save_halts_new_creations(setup, monkeypatch):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    original_finish = context.usage.finish
    def save_failure(attempt_id, state, **kwargs):
        if state == 'SUBMITTED':
            raise ServiceError('NEURAL4D_LEDGER_UNAVAILABLE', '仅离线模拟收到UUID后本地写入失败。', 503)
        return original_finish(attempt_id, state, **kwargs)
    monkeypatch.setattr(context.usage, 'finish', save_failure)
    with pytest.raises(ServiceError, match='NEURAL4D_LEDGER_UNAVAILABLE'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-save-failure'))
    assert context.usage.summary()['creationHalted']
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1
    with pytest.raises(ServiceError):
        context.models.approve(prepared(context))


def test_conflicting_uuid_fields_never_hide_additional_provider_model(setup):
    def handler(request):
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        return httpx.Response(200, json={'uuid': 'offline-unexpected-extra', 'uuids': ['offline-main']})
    context = setup(handler, enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    with pytest.raises(ServiceError, match='NEURAL4D_RESPONSE_INVALID'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-conflicting-response'))
    assert context.usage.summary()['creationHalted']
    assert context.usage.summary()['attemptStates'] == {'UNKNOWN': 1}


@pytest.mark.parametrize('token', [None, '', 'wrong-ascii-token', '错误的授权内容', 123])
def test_management_authorization_rejects_untrusted_token_without_internal_errors(setup, token):
    context = setup()
    with pytest.raises(ServiceError, match='ASSET_AUTH_REQUIRED'):
        context.models.authorize(token)
    assert context.calls == []


def test_explicit_refresh_keeps_original_job_and_links_validated_real_glb_fixture(setup, monkeypatch):
    calls, query_count = [], [0]
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-async-original-job'})
        if request.url.path.endswith('retrieveModel'):
            assert json.loads(request.content)['uuid'] == 'offline-async-original-job'
            query_count[0] += 1
            if query_count[0] == 1:
                return httpx.Response(200, json={'codeStatus': 1})
            return httpx.Response(200, json={'codeStatus': 0, 'modelUrl': f'https://{DOWNLOAD_HOST}/fixture.glb?signature=offline'})
        assert request.method == 'GET' and 'authorization' not in request.headers
        return httpx.Response(200, content=glb())
    context = setup(handler, enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-async-original'))
    # Switching off creation never prevents reading/downloading the original job.
    context.settings.neural4d_generation_enabled = False
    clock = [time.time()]
    monkeypatch.setattr('backend.app.assets.neural_service.time.time', lambda: clock[0])
    assert context.models.status(submitted['jobId'])['state'] == 'SUBMITTED'
    assert sum(r.url.path.endswith('retrieveModel') for r in calls) == 0
    running = asyncio.run(context.models.refresh(submitted['jobId']))
    clock[0] += 16
    ready = asyncio.run(context.models.refresh(submitted['jobId']))
    clock[0] += 16
    again = asyncio.run(context.models.refresh(submitted['jobId']))
    assert running['state'] == 'PROCESSING' and ready['state'] == 'SUCCEEDED'
    assert ready['model']['format'] == 'glb' and ready['model']['validation']['valid']
    assert ready['model']['origin'] == 'neural4d'  # mock contract value only, no real generation
    assert ready['model']['imageHash'] == data['imageHash']
    assert ready['model']['modelId'] == again['model']['modelId']
    character = context.assets.get_character(data['assetId'])
    assert ready['model']['sourceResultHash'] == character['sourceResultHash']
    assert ready['model']['citationHash'] == character['citationHash']
    assert len(context.assets.list_models()) == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    assert context.usage.summary()['occupied_attempts'] == 1


def test_corrupt_download_never_becomes_ready_or_trigger_new_model(setup):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-corrupt-output'})
        if request.url.path.endswith('retrieveModel'):
            return httpx.Response(200, json={'codeStatus': 0, 'modelUrl': f'https://{DOWNLOAD_HOST}/invalid.glb'})
        return httpx.Response(200, content=b'HTTP200 is not a real GLB model')
    context = setup(handler, enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-corrupt-model'))
    with pytest.raises(ServiceError, match='MODEL_INVALID'):
        asyncio.run(context.models.refresh(submitted['jobId']))
    assert context.models.status(submitted['jobId'])['state'] != 'SUCCEEDED'
    assert context.assets.list_models() == []
    assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    assert context.usage.summary()['occupied_attempts'] == 1


@pytest.mark.parametrize('invalid_code', [False, True, '0', None])
def test_malformed_query_status_does_not_claim_success_or_real_progress(setup, invalid_code):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-malformed-query'})
        if request.url.path.endswith('retrieveModel'):
            return httpx.Response(200, json={'codeStatus': invalid_code, 'modelUrl': f'https://{DOWNLOAD_HOST}/fixture.glb'})
        return httpx.Response(200, content=glb())
    context = setup(handler, enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-invalid-query-code'))
    with pytest.raises(ServiceError, match='NEURAL4D_RECONCILIATION_REQUIRED'):
        asyncio.run(context.models.refresh(submitted['jobId']))
    assert context.models.status(submitted['jobId'])['state'] == 'PENDING_RECONCILIATION'
    assert context.models.status(submitted['jobId'])['providerTaskId'] == 'offline-malformed-query'
    assert context.usage.summary()['creationPaused'] is True
    assert context.usage.summary()['occupied_attempts'] == 1
    assert not any(r.method == 'GET' for r in requests)


def test_query_throttle_restart_race_and_explicit_continuation_preserve_counts(setup, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-query-limit-task'})
        return httpx.Response(200, json={'codeStatus': 1})
    context = setup(handler, enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-query-limits'))
    job_id = submitted['jobId']
    clock = [time.time()]
    monkeypatch.setattr('backend.app.assets.neural_service.time.time', lambda: clock[0])
    assert asyncio.run(context.models.refresh(job_id))['state'] == 'PROCESSING'
    context.models.close()
    reopened = ModelService(context.settings, context.assets, UsageManager(context.usage.path), context.transport)
    try:
        reopened.start()
        with pytest.raises(ServiceError, match='NEURAL4D_QUERY_TOO_SOON'):
            asyncio.run(reopened.refresh(job_id))
        assert sum(r.url.path.endswith('retrieveModel') for r in calls) == 1
        clock[0] += 16
        barrier = Barrier(2)
        def race_claim():
            barrier.wait()
            try:
                reopened.claim_query(job_id)
                return 'one-query-claim'
            except ServiceError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(lambda _: race_claim(), range(2)))
        assert sorted(outcomes) == ['NEURAL4D_QUERY_TOO_SOON', 'one-query-claim']
        for _ in range(18):
            clock[0] += 16
            reopened.claim_query(job_id)
        clock[0] += 16
        with pytest.raises(ServiceError, match='NEURAL4D_QUERY_CONFIRMATION_REQUIRED'):
            reopened.claim_query(job_id)
        reopened.authorize(FAKE_ADMIN)
        assert reopened.continue_queries(job_id)['queryContinuationAccepted']
        reopened.claim_query(job_id)
        with context.assets.store.connect() as db:
            row = db.execute('SELECT * FROM neural4d_query_limits WHERE job_id=?', (job_id,)).fetchone()
        assert row['total_count'] == 21 and row['series_count'] == 1
        assert context.usage.summary()['occupied_attempts'] == 1
        assert sum(r.url.path.endswith('generateModelWithImage') for r in calls) == 1
    finally:
        reopened.close()


@pytest.mark.parametrize('style,faces', [('chibi', '100000'), ('realistic', '500000')])
def test_each_style_uses_confirmed_image_and_single_model_server_preset(setup, style, faces):
    context = setup(enabled=True, protocol=True)
    data = prepared(context, style_mode=style)
    confirmation = approve(context, data)
    frozen = context.models.approval_payload(confirmation['approvalId'])
    assert frozen['styleMode'] == style and frozen['styleVersion'] == data['styleVersion']
    assert frozen['characterId'] == data['characterId'] and frozen['imageHash'] == data['imageHash']
    assert frozen['parameters'] == parameters_for_style(style)
    assert frozen['parameters']['faceNum'] == faces and frozen['parameters']['modelCount'] == '1'
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, f'offline-style-{style}'))
    assert submitted['styleMode'] == style and submitted['characterId'] == data['characterId']
    requests = [r for r in context.calls if r.url.path.endswith('generateModelWithImage')]
    assert len(requests) == 1
    body = requests[0].content
    assert b'name="faceNum"\r\n\r\n' + faces.encode() + b'\r\n' in body
    assert b'name="modelCount"\r\n\r\n1\r\n' in body
    assert b'name="disablePbr"\r\n\r\n0\r\n' in body
    assert context.usage.summary()['occupied_attempts'] == 1


def test_styles_share_one_character_but_only_three_total_creation_attempts(setup):
    context = setup(enabled=True, protocol=True)
    first = prepared(context, style_mode='chibi')
    source_task = context.assets.get_character(first['assetId'])['sourceTaskId']
    second = prepared(context, style_mode='realistic', source_task_id=source_task)
    assert first['characterId'] == second['characterId'] and first['assetId'] != second['assetId']
    assert first['promptHash'] != second['promptHash']
    third = prepared(context, style_mode='chibi', source_task_id=source_task, purpose='独立人工确认的第三次离线尝试')
    for index, data in enumerate((first, second, third)):
        confirmation = approve(context, data)
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, f'offline-mixed-style-{index}'))
    assert context.usage.summary()['occupied_attempts'] == 3 and context.usage.summary()['remaining_attempts'] == 0
    for style in ('chibi', 'realistic'):
        with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
            context.models.approve(prepared(context, style_mode=style, purpose=f'拒绝第四次-{style}'))
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 3


def test_concurrent_mixed_style_submissions_still_share_atomic_three_cap(setup):
    requests = []
    async def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        number = sum(r.url.path.endswith('generateModelWithImage') for r in requests)
        # Actual coroutine overlap: three claims can persist while mock send is
        # suspended; the fourth must still be rejected before any send.
        await asyncio.sleep(0.03)
        return httpx.Response(200, json={'uuid': f'offline-overlap-style-{number}'})
    context = setup(handler, enabled=True, protocol=True)
    candidates = [prepared(context, style_mode='chibi' if i % 2 == 0 else 'realistic', purpose=f'离线跨风格并发{i}') for i in range(4)]
    approvals = [approve(context, data) for data in candidates]
    async def submit_all():
        return await asyncio.gather(*(context.models.submit({'approvalId': approval['approvalId'], 'modelCount': 1}, f'offline-global-style-{i}')
                                      for i, approval in enumerate(approvals)), return_exceptions=True)
    results = asyncio.run(submit_all())
    assert sum(isinstance(r, dict) and r['state'] == 'SUBMITTED' for r in results) == 3
    assert sum(isinstance(r, ServiceError) and r.code == 'NEURAL4D_QUOTA_EXHAUSTED' for r in results) == 1
    assert context.usage.summary()['occupied_attempts'] == 3
    creation_requests = [r for r in requests if r.url.path.endswith('generateModelWithImage')]
    assert len(creation_requests) == 3 and all(b'name="modelCount"\r\n\r\n1\r\n' in r.content for r in creation_requests)


@pytest.mark.parametrize('field,changed', [('styleMode', 'chibi'), ('styleVersion', 2), ('characterId', '11111111-1111-1111-1111-111111111111'), ('styleVersion', True)])
def test_approval_cannot_rebind_other_style_version_or_character(setup, field, changed):
    context = setup(enabled=True, protocol=True)
    data = prepared(context, style_mode='realistic')
    asyncio.run(context.models.verify())
    with pytest.raises(ServiceError, match='NEURAL4D_INPUT_CHANGED'):
        context.models.approve({**data, field: changed})
    assert context.usage.summary()['occupied_attempts'] == 0
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_stale_approval_without_style_binding_never_uses_new_preset(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    for field in ('styleMode', 'styleVersion', 'characterId'):
        payload.pop(field)
    with context.assets.store.connect() as db:
        db.execute('UPDATE neural4d_frozen_approvals SET payload_json=? WHERE approval_id=?', (json.dumps(payload), confirmation['approvalId']))
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-legacy-approval'))
    assert context.usage.summary()['occupied_attempts'] == 0
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_free_prompt_cultural_review_gate_cannot_be_bypassed_by_generation_approval(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    asyncio.run(context.models.verify())
    stored = context.assets.store.get(data['assetId'])
    stored['culturalReviewRequired'] = True
    with context.assets.store.connect() as db:
        db.execute('UPDATE character_assets SET content_json=? WHERE asset_id=?', (json.dumps(stored), data['assetId']))
    with pytest.raises(ServiceError, match='ASSET_CULTURAL_REVIEW_REQUIRED'):
        context.models.approve(data)
    assert context.usage.summary()['occupied_attempts'] == 0
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_provider_never_accepts_client_selected_multipart_parameters(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context, style_mode='chibi')
    asyncio.run(context.models.verify())
    frozen = context.models.freeze(data)
    frozen['parameters'] = {**frozen['parameters'], 'faceNum': '500000', 'modelCount': '2'}
    confirmation = context.usage.approve(frozen, data['purpose'], confirmed=True, estimated_credits=80)
    attempt = context.usage.reserve('offline-bad-param-map', confirmation['approvalId'], frozen, data['purpose'], True, True)
    with pytest.raises(ServiceError, match='NEURAL4D_INPUT_CHANGED'):
        asyncio.run(context.provider.create_once(attempt['attemptId'], context.assets.file_path('image', data['imageId']).read_bytes()))
    assert context.usage.get_attempt(attempt['attemptId'])['state'] == 'RESERVED'
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def edited_prompt(context, data):
    previous = context.assets.get_character(data['assetId'])
    prompt = previous['visualPrompt']
    return context.assets.create_prompt_version(data['assetId'], {
        'expectedPromptHash': prompt['promptHash'], 'imagePrompt': prompt['imagePrompt'] + '\n离线新增Prompt草稿版本测试。',
        'negativePrompt': prompt['negativePrompt'], 'action': 'create_version'})


def test_new_prompt_version_invalidates_old_unsent_approval_before_quota_or_send(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    new = edited_prompt(context, data)
    assert new['styleVersion'] == data['styleVersion'] + 1 and new['culturalReviewRequired']
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        context.models.approve(data)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-stale-unsent'))
    assert context.usage.summary()['occupied_attempts'] == 0
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_new_prompt_version_does_not_invalidate_other_style_approval(setup):
    context = setup(enabled=True, protocol=True)
    realistic = prepared(context, style_mode='realistic')
    source_task = context.assets.get_character(realistic['assetId'])['sourceTaskId']
    chibi = prepared(context, style_mode='chibi', source_task_id=source_task)
    confirmation = approve(context, chibi)
    edited_prompt(context, realistic)
    assert chibi['characterId'] == realistic['characterId']
    submitted = asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-unrelated-style'))
    assert submitted['styleMode'] == 'chibi' and submitted['state'] == 'SUBMITTED'
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1


def test_sent_same_key_replay_after_prompt_edit_keeps_original_job_and_download(setup):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-historical-style-job'})
        if request.url.path.endswith('retrieveModel'):
            assert json.loads(request.content)['uuid'] == 'offline-historical-style-job'
            return httpx.Response(200, json={'codeStatus': 0, 'modelUrl': f'https://{DOWNLOAD_HOST}/historical.glb'})
        return httpx.Response(200, content=glb())
    context = setup(handler, enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    request = {'approvalId': confirmation['approvalId'], 'modelCount': 1}
    original = asyncio.run(context.models.submit(request, 'offline-historical-style-key'))
    edited_prompt(context, data)
    replay = asyncio.run(context.models.submit(request, 'offline-historical-style-key'))
    assert replay['attemptId'] == original['attemptId'] and not replay['newlyReserved']
    assert replay['styleVersion'] == data['styleVersion']
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        asyncio.run(context.models.submit(request, 'offline-different-key-not-replay'))
    completed = asyncio.run(context.models.refresh(original['jobId']))
    assert completed['state'] == 'SUCCEEDED' and completed['model']['assetId'] == data['assetId']
    assert completed['model']['styleVersion'] == data['styleVersion']
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in requests) == 1


def test_reserved_but_unsent_same_key_does_not_bypass_new_prompt_version(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    reserved = context.usage.reserve('offline-reserved-old-version', confirmation['approvalId'], payload, data['purpose'], True, True)
    edited_prompt(context, data)
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-reserved-old-version'))
    assert context.usage.get_attempt(reserved['attemptId'])['state'] == 'RESERVED'
    assert context.usage.get_attempt(reserved['attemptId'])['startedAt'] is None
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_sent_key_cannot_replay_another_approval_or_style(setup):
    context = setup(enabled=True, protocol=True)
    first = prepared(context, style_mode='realistic')
    source_task = context.assets.get_character(first['assetId'])['sourceTaskId']
    second = prepared(context, style_mode='chibi', source_task_id=source_task)
    confirmation = approve(context, first)
    asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-shared-conflict-key'))
    another = context.models.approve(second)
    with pytest.raises(ServiceError, match='NEURAL4D_IDEMPOTENCY_CONFLICT'):
        asyncio.run(context.models.submit({'approvalId': another['approvalId'], 'modelCount': 1}, 'offline-shared-conflict-key'))
    assert context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1


@pytest.mark.parametrize('transport', [None, httpx.AsyncHTTPTransport()])
def test_real_or_custom_provider_cannot_choose_fresh_noncanonical_ledger(setup, transport):
    context = setup()
    with pytest.raises(ServiceError, match='NEURAL4D_LEDGER_PATH_INVALID'):
        Neural4DProvider(context.settings, context.usage, transport)
    assert context.calls == [] and context.usage.summary()['occupied_attempts'] == 0


def test_switching_mock_provider_to_real_transport_rechecks_canonical_before_send(setup):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    confirmation = approve(context, data)
    payload = context.models.approval_payload(confirmation['approvalId'])
    reserved = context.usage.reserve('offline-no-real-ledger-bypass', confirmation['approvalId'], payload, data['purpose'], True, True)
    context.provider.transport = None
    with pytest.raises(ServiceError, match='NEURAL4D_LEDGER_PATH_INVALID'):
        asyncio.run(context.provider.create_once(reserved['attemptId'], context.assets.file_path('image', data['imageId']).read_bytes()))
    assert context.usage.get_attempt(reserved['attemptId'])['state'] == 'RESERVED'
    assert context.usage.get_attempt(reserved['attemptId'])['startedAt'] is None
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


@pytest.mark.parametrize('new_price', [81, 1000, None])
def test_unsent_approval_rejects_changed_or_unverified_cost_before_reserve_and_send(setup, new_price):
    context = setup(enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    context.settings.neural4d_expected_credits = new_price
    with pytest.raises(ServiceError, match='NEURAL4D_COST_CHANGED'):
        asyncio.run(context.models.submit({'approvalId': confirmation['approvalId'], 'modelCount': 1}, 'offline-changed-price'))
    assert context.usage.approval_estimated_credits(confirmation['approvalId']) == 80
    assert context.usage.summary()['occupied_attempts'] == 0
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 0


def test_sent_same_key_replay_after_price_change_only_reads_original_task(setup):
    context = setup(enabled=True, protocol=True)
    confirmation = approve(context, prepared(context))
    request = {'approvalId': confirmation['approvalId'], 'modelCount': 1}
    original = asyncio.run(context.models.submit(request, 'offline-price-replay'))
    context.settings.neural4d_expected_credits = 1000  # exceeds known fixture balance
    replay = asyncio.run(context.models.submit(request, 'offline-price-replay'))
    assert replay['attemptId'] == original['attemptId'] and replay['estimatedCredits'] == 80
    assert not replay['newlyReserved'] and context.usage.summary()['occupied_attempts'] == 1
    assert sum(r.url.path.endswith('generateModelWithImage') for r in context.calls) == 1


class OfflineCustomTransport(httpx.AsyncBaseTransport):
    """Classification fixture, with no HTTP backend/socket/network behavior.

    Deliberately not MockTransport so production-style policy is exercised. The
    test patches only its temporary ledger as canonical, never the real ledger.
    """
    def __init__(self):
        self.requests = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'offline-custom-classification-only'})
        return httpx.Response(200, content=glb())


def test_custom_transport_with_isolated_canonical_fixture_is_not_logged_as_mock(setup, monkeypatch):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    payload = context.models.freeze(data)
    confirmation = context.usage.approve(payload, data['purpose'], confirmed=True, estimated_credits=80)
    attempt = context.usage.reserve('offline-custom-classification', confirmation['approvalId'], payload, data['purpose'], True, True)
    monkeypatch.setattr('backend.app.providers.neural4d.CANONICAL_USAGE_LEDGER', context.usage.path)
    transport = OfflineCustomTransport()
    provider = Neural4DProvider(context.settings, context.usage, transport)
    assert not provider.is_mock
    asyncio.run(provider.read_operation('queryPointsInfo', {}, 'verify'))
    asyncio.run(provider.create_once(attempt['attemptId'], context.assets.file_path('image', data['imageId']).read_bytes()))
    # An arbitrary custom transport cannot replace the DNS-pinned production
    # downloader. Only explicit MockTransport is accepted for offline download
    # tests; supplier-operation accounting still classifies this as non-mock.
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(provider.download(f'https://{DOWNLOAD_HOST}/custom-contract.glb'))
    assert len(transport.requests) == 2
    with context.usage.connect() as db:
        rows = list(db.execute('SELECT operation,is_mock FROM neural4d_operational_requests ORDER BY operation'))
    assert [(r['operation'], r['is_mock']) for r in rows] == [('create_model', 0), ('verify', 0)]
    # This is only accounting in the temporary test ledger; no real HTTP was sent.
    assert context.usage.summary()['realHttpRequests'] == 2 and context.usage.summary()['mockHttpRequests'] == 0


def test_custom_transport_does_not_bypass_private_download_address_check(setup, monkeypatch):
    context = setup()
    monkeypatch.setattr('backend.app.providers.neural4d.CANONICAL_USAGE_LEDGER', context.usage.path)
    transport = OfflineCustomTransport()
    provider = Neural4DProvider(context.settings, context.usage, transport)
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(provider.download(f'https://{DOWNLOAD_HOST}/private-contract.glb'))
    assert transport.requests == []
    assert context.usage.summary()['realHttpRequests'] == 0
