"""OFFLINE integration of the scoped internal model path.

Every supplier response is httpx.MockTransport; generated images and temporary
SQLite files are synthetic. Duck.glb is the licensed, existing browser fixture,
not a generated opera model or evidence of any real Neural4D call. DNS is denied.
"""
import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.assets.candidates import CandidateCatalog
from backend.app.assets.schemas import ModelApprovalRequest
from backend.app.assets.technical_test import register_technical_model
from backend.app.errors import ServiceError
from backend.tests.test_phase4_assets import api, image_bytes
from backend.tests.test_phase4_neural4d import (DOWNLOAD_HOST, FAKE_ADMIN, FAKE_KEY,
                                              approve, no_dns, prepared, setup)


DUCK = Path(__file__).parent / 'fixtures' / 'phase4' / 'Duck.glb'
SCOPE = 'OFFLINE_INTERNAL_CHIBI_INTEGRATION'


def technical_input(context, *, text='离线内部技术验证Prompt', scope=SCOPE):
    """An unassociated v2 candidate, with no synthetic cultural approval."""
    catalog = CandidateCatalog(context.assets)
    if not catalog.list(scope=scope):
        catalog.import_history({'sha256': '1' * 64, 'styleMode': 'chibi',
                                'source': 'OFFLINE historical metadata only'}, scope)
    current = catalog.register(image_bytes(), 'image/png', scope,
                               'OFFLINE synthetic image', 'OFFLINE test permission',
                               {'version': 'offline-internal-prompt-v1', 'text': text},
                               styleMode='chibi')
    assert current['version'] >= 2 and current['accepted'] is False
    return {'candidateId': current['candidateId'], 'sourceImageHash': current['sourceHash'],
            'imageHash': current['hash'], 'promptHash': current['promptSnapshot']['promptHash'],
            'styleMode': 'chibi', 'purpose': '技术验证', 'modelCount': 1,
            'authorizationEvidenceHash': 'a' * 64, 'permissionEvidenceHash': 'b' * 64,
            'action': 'accept', 'estimatedCredits': 30}


def ready(context):
    context.settings.neural4d_expected_credits = 30
    asyncio.run(context.models.verify())


def send(context, approval, key='offline-internal-once'):
    return asyncio.run(context.models.submit({'approvalId': approval['approvalId'], 'modelCount': 1}, key))


def create_calls(context):
    return [request for request in context.calls if request.url.path.endswith('generateModelWithImage')]


def client_for(context, peer='127.0.0.1', host='127.0.0.1', headers=None):
    return TestClient(api(context.assets).app, base_url=f'http://{host}',
                      client=(peer, 50000), headers=headers)


def saved_mock_model(context, *, provider_id='OFFLINE-generated-task'):
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    payload = context.models.approval_payload(approval['approvalId'])
    model = register_technical_model(context.assets, payload, DUCK.read_bytes(), provider_id)
    return model


def test_internal_shared_sender_freezes_once_and_idempotent_replay_has_no_second_send(setup):
    context = setup(enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    payload = context.models.approval_payload(approval['approvalId'])
    assert payload['assetKind'] == 'internal_technical_test'
    assert payload['characterId'] is payload['assetId'] is payload['sourceTaskId'] is None
    assert payload['internalUseOnly'] is True and payload['publicationAllowed'] is False
    assert payload['imageHash'] == data['imageHash'] and payload['promptHash'] == data['promptHash']
    assert context.usage.summary()['occupied_attempts'] == 0

    first = send(context, approval)
    replay = send(context, approval)
    assert first['jobId'] == replay['jobId'] and first['state'] == replay['state'] == 'SUBMITTED'
    assert first['candidateId'] == data['candidateId'] and first['assetId'] is None
    assert len(create_calls(context)) == 1
    body = create_calls(context)[0].content
    assert body.count(b'name="modelCount"') == 1
    assert b'name="modelCount"\r\n\r\n1\r\n' in body
    assert b'name="faceNum"\r\n\r\n100000\r\n' in body
    assert b'name="image"; filename="concept.png"' in body
    assert context.usage.summary()['remaining_attempts'] == 2
    assert context.usage.summary()['realHttpRequests'] == 0
    assert context.usage.summary()['mockHttpRequests'] == 2
    with context.assets.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM character_assets').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM asset_images').fetchone()[0] == 0


def test_concurrent_internal_clicks_share_one_atomic_send(setup):
    requests = []
    async def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        await asyncio.sleep(0.03)
        return httpx.Response(200, json={'uuid': 'OFFLINE-internal-race'})

    context = setup(handler, enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    async def race():
        request = {'approvalId': approval['approvalId'], 'modelCount': 1}
        return await asyncio.gather(context.models.submit(request, 'offline-internal-race'),
                                    context.models.submit(request, 'offline-internal-race'))
    results = asyncio.run(race())
    assert results[0]['attemptId'] == results[1]['attemptId']
    assert sum(request.url.path.endswith('generateModelWithImage') for request in requests) == 1
    assert context.usage.summary()['occupied_attempts'] == 1


def test_internal_approval_cannot_be_sent_with_new_key_after_one_send(setup):
    context = setup(enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    send(context, approval)
    with pytest.raises(ServiceError):
        send(context, approval, 'offline-internal-new-key')
    assert len(create_calls(context)) == 1
    assert context.usage.summary()['occupied_attempts'] == 1


@pytest.mark.parametrize('mutation', [{'action': 'preview'}, {'estimatedCredits': 20},
                                     {'publicationAllowed': True}, {'modelCount': 2},
                                     {'styleMode': 'realistic'}, {'characterId': 'forged-role'}])
def test_ungranted_confirmation_cost_identity_or_style_cannot_reach_sender(setup, mutation):
    context = setup(enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    with pytest.raises(ServiceError):
        context.models.approve_technical_candidate({**data, **mutation})
    assert create_calls(context) == []
    assert context.usage.summary()['occupied_attempts'] == 0


@pytest.mark.parametrize('condition', ['disabled', 'protocol', 'history', 'balance'])
def test_internal_exception_does_not_relax_shared_readiness_gates(setup, condition):
    context = setup(enabled=condition != 'disabled', protocol=True,
                    history=None if condition == 'history' else 0)
    data = technical_input(context)
    ready(context)
    if condition == 'protocol':
        context.settings.neural4d_protocol_verified = False
    if condition == 'balance':
        context.models.balance = 0  # Isolated negative-condition injection.
    with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
        context.models.approve_technical_candidate(data)
    assert create_calls(context) == [] and context.usage.summary()['attemptStates'] == {}


def test_new_candidate_revision_blocks_existing_unsent_internal_approval(setup):
    context = setup(enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    technical_input(context, text='OFFLINE newer immutable review revision')
    with pytest.raises(ServiceError, match='NEURAL4D_APPROVAL_STALE'):
        send(context, approval)
    assert create_calls(context) == [] and context.usage.summary()['occupied_attempts'] == 0


@pytest.mark.parametrize('first_kind', ['technical', 'formal'])
@pytest.mark.parametrize('unknown_state', ['UNKNOWN', 'PENDING_RECONCILIATION'])
def test_unknown_pauses_shared_formal_and_internal_paths_without_refund(setup, first_kind, unknown_state):
    context = setup(enabled=True, protocol=True)
    technical = technical_input(context)
    formal = prepared(context, style_mode='realistic')
    formal['estimatedCredits'] = 30
    ready(context)
    confirmations = {'technical': context.models.approve_technical_candidate(technical),
                     'formal': context.models.approve(formal)}
    first = send(context, confirmations[first_kind], 'offline-shared-first')
    context.usage.finish(first['jobId'], unknown_state, error_code='OFFLINE_RECONCILIATION')
    assert context.models.available() is False
    assert context.usage.summary()['creationPaused'] is True
    for data, method in ((technical, context.models.approve_technical_candidate), (formal, context.models.approve)):
        with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
            method(data)
    other = 'formal' if first_kind == 'technical' else 'technical'
    with pytest.raises(ServiceError, match='NEURAL4D_RECONCILIATION_REQUIRED'):
        send(context, confirmations[other], 'offline-shared-other')
    replay = send(context, confirmations[first_kind], 'offline-shared-first')
    assert replay['jobId'] == first['jobId'] and replay['state'] == unknown_state
    assert len(create_calls(context)) == 1
    assert context.usage.summary()['occupied_attempts'] == 1
    assert context.usage.summary()['remaining_attempts'] == 2


def test_three_global_attempts_are_shared_by_internal_chibi_formal_chibi_and_realistic(setup):
    context = setup(enabled=True, protocol=True)
    technical = technical_input(context)
    formal_chibi = prepared(context, style_mode='chibi', purpose='OFFLINE formal chibi')
    formal_realistic = prepared(context, style_mode='realistic', purpose='OFFLINE formal realistic')
    ready(context)
    approvals = [context.models.approve_technical_candidate(technical)]
    for data in (formal_chibi, formal_realistic):
        approvals.append(context.models.approve({**data, 'estimatedCredits': 30}))
    future = context.models.approve_technical_candidate(technical)
    for index, approval in enumerate(approvals):
        send(context, approval, f'offline-shared-cap-{index}')
    assert len(create_calls(context)) == 3
    summary = context.usage.summary()
    assert summary['max_creation_attempts'] == summary['max_models'] == 3
    assert summary['occupied_attempts'] == 3 and summary['remaining_attempts'] == 0
    assert context.models.available() is False
    with pytest.raises(ServiceError):
        send(context, future, 'offline-shared-cap-fourth')
    assert len(create_calls(context)) == 3


def test_mock_generation_download_preserves_internal_lineage_and_actual_credit_record(setup):
    requests = []
    raw = DUCK.read_bytes()
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'OFFLINE-internal-download', 'pointsDeducted': 30})
        if request.url.path.endswith('retrieveModel'):
            assert json.loads(request.content) == {'uuid': 'OFFLINE-internal-download'}
            return httpx.Response(200, json={'codeStatus': 0,
                                           'modelUrl': f'https://{DOWNLOAD_HOST}/offline-duck.glb'})
        assert request.url.host == DOWNLOAD_HOST and 'authorization' not in request.headers
        return httpx.Response(200, content=raw)

    context = setup(handler, enabled=True, protocol=True)
    data = technical_input(context)
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    sent = send(context, approval)
    result = asyncio.run(context.models.refresh(sent['jobId']))
    assert result['state'] == 'SUCCEEDED'
    model = result['model']
    assert model['hash'] == hashlib.sha256(raw).hexdigest()
    assert context.assets.file_path('model', model['modelId']).read_bytes() == raw
    assert model['origin'] == 'neural4d_technical_test'
    assert model['candidateId'] == data['candidateId'] and model['characterId'] is None
    assert model['publicationAllowed'] is False and model['internalUseOnly'] is True
    assert context.assets.list_models() == []
    assert context.usage.summary()['recordedActualCredits'] == 0  # Mock is never actual-account spend.
    assert context.usage.summary()['realHttpRequests'] == 0
    assert context.usage.summary()['mockHttpRequests'] == 4
    with context.usage.connect() as db:
        row = dict(db.execute("SELECT * FROM neural4d_operational_requests WHERE operation='create_model'").fetchone())
    assert row['is_mock'] == 1 and row['actual_credits'] == 30
    assert row['attempt_id'] == sent['jobId'] and row['http_status'] == 200
    assert FAKE_KEY not in json.dumps(row)
    assert sum(request.url.path.endswith('generateModelWithImage') for request in requests) == 1


@pytest.mark.parametrize('failure', ['unknown_code', 'string_code', 'query_timeout', 'invalid_glb'])
def test_uncertain_query_or_result_keeps_original_task_and_pauses_new_creation(setup, failure):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('queryPointsInfo'):
            return httpx.Response(200, json={'statusType': 0, 'data': {'total_points': 800}})
        if request.url.path.endswith('generateModelWithImage'):
            return httpx.Response(200, json={'uuid': 'OFFLINE-query-reconciliation'})
        if request.url.path.endswith('retrieveModel'):
            if failure == 'query_timeout':
                raise httpx.ReadTimeout('OFFLINE query timeout', request=request)
            if failure == 'invalid_glb':
                return httpx.Response(200, json={'codeStatus': 0,
                                               'modelUrl': f'https://{DOWNLOAD_HOST}/invalid.glb'})
            return httpx.Response(200, json={'codeStatus': '0' if failure == 'string_code' else 999})
        return httpx.Response(200, content=b'OFFLINE corrupt model; not GLB')

    context = setup(handler, enabled=True, protocol=True)
    data = technical_input(context)
    formal = {**prepared(context), 'estimatedCredits': 30}
    ready(context)
    approval = context.models.approve_technical_candidate(data)
    sent = send(context, approval)
    with pytest.raises(ServiceError):
        asyncio.run(context.models.refresh(sent['jobId']))
    persisted = context.usage.get_attempt(sent['jobId'])
    assert persisted['state'] == 'PENDING_RECONCILIATION'
    assert persisted['providerTaskId'] == 'OFFLINE-query-reconciliation'
    assert context.usage.summary()['creationPaused'] is True
    assert context.usage.summary()['occupied_attempts'] == 1
    assert context.usage.summary()['remaining_attempts'] == 2
    for request, method in ((data, context.models.approve_technical_candidate), (formal, context.models.approve)):
        with pytest.raises(ServiceError, match='NEURAL4D_GENERATION_DISABLED'):
            method(request)
    replay = send(context, approval)
    assert replay['providerTaskId'] == persisted['providerTaskId']
    assert replay['state'] == 'PENDING_RECONCILIATION'
    assert sum(request.url.path.endswith('generateModelWithImage') for request in requests) == 1
    assert context.assets.list_models() == []


@pytest.mark.parametrize('inject', [{'assetKind': 'internal_technical_test'},
                                  {'candidateId': '00000000-0000-0000-0000-000000000001'},
                                  {'internalUseOnly': True}, {'visibility': 'internal'},
                                  {'permissionEvidenceHash': 'b' * 64}])
def test_formal_browser_approval_schema_rejects_candidate_type_bypass(setup, inject):
    context = setup(enabled=True, protocol=True)
    data = prepared(context)
    with pytest.raises(ValidationError):
        ModelApprovalRequest.model_validate({**data, **inject})
    response = api(context.assets).post('/api/v1/assets/model-approvals', json={**data, **inject},
                                        headers={'X-Asset-Admin-Token': FAKE_ADMIN})
    assert response.status_code == 422
    assert context.calls == [] and context.usage.summary()['occupied_attempts'] == 0


def test_candidate_uuid_substitution_cannot_impersonate_formal_asset_or_accepted_image(setup):
    context = setup(enabled=True, protocol=True)
    candidate = technical_input(context)
    formal = prepared(context)
    ready(context)
    request = {**formal, 'assetId': candidate['candidateId'], 'imageId': candidate['candidateId'],
               'estimatedCredits': 30}
    response = api(context.assets).post('/api/v1/assets/model-approvals', json=request,
                                        headers={'X-Asset-Admin-Token': FAKE_ADMIN})
    assert response.status_code == 404
    assert create_calls(context) == [] and context.usage.summary()['occupied_attempts'] == 0


@pytest.mark.parametrize('peer,host', [('testclient', 'testserver'), ('testclient', '127.0.0.1'),
                                     ('203.0.113.4', '127.0.0.1'), ('127.0.0.1', 'example.invalid')])
@pytest.mark.parametrize('suffix', ['', '/file', '/download', '/viewer'])
def test_internal_model_metadata_files_and_viewer_require_loopback_peer_and_host(setup, peer, host, suffix):
    context = setup(enabled=True, protocol=True)
    model = saved_mock_model(context)
    base = 'internal-models' if suffix == '/viewer' else 'models'
    url = f"/api/v1/assets/{base}/{model['modelId']}{suffix}"
    assert client_for(context, peer, host).get(url).status_code == 404
    assert api(context.assets).get('/api/v1/assets/models').json()['models'] == []
    assert context.usage.summary()['occupied_attempts'] == 0


@pytest.mark.parametrize('host', ['127.0.0.1', 'localhost'])
def test_loopback_internal_file_and_viewer_use_actual_model_and_no_store(setup, host):
    context = setup(enabled=True, protocol=True)
    model = saved_mock_model(context)
    client = client_for(context, host=host)
    metadata = client.get(f"/api/v1/assets/models/{model['modelId']}")
    assert metadata.status_code == 200 and metadata.json()['modelId'] == model['modelId']
    file = client.get(f"/api/v1/assets/models/{model['modelId']}/file")
    assert file.status_code == 200 and file.content == DUCK.read_bytes()
    assert file.headers['cache-control'] == 'private, no-store'
    assert file.headers['etag'] == f'"{model["hash"]}"'
    viewer = client.get(f"/api/v1/assets/internal-models/{model['modelId']}/viewer")
    assert viewer.status_code == 200 and '非正式角色资产' in viewer.text
    assert model['modelId'] in viewer.text and model['providerTaskId'] in viewer.text
    assert viewer.headers['cache-control'] == 'private, no-store'
    assert 'frame-ancestors' in viewer.headers['content-security-policy']
    policy = viewer.headers['content-security-policy']
    script_rule = next(rule.strip() for rule in policy.split(';') if rule.strip().startswith('script-src '))
    assert script_rule == "script-src 'self' 'wasm-unsafe-eval'"
    assert "'unsafe-eval'" not in policy and "script-src 'unsafe-inline'" not in policy
    assert '/js/ai-workshop/internal-viewer.js' in viewer.text
    assert context.usage.summary()['occupied_attempts'] == 0


@pytest.mark.parametrize('suffix', ['/file', '/download', '/viewer'])
def test_cross_site_browser_access_to_internal_model_is_rejected(setup, suffix):
    context = setup(enabled=True, protocol=True)
    model = saved_mock_model(context)
    base = 'internal-models' if suffix == '/viewer' else 'models'
    client = client_for(context, headers={'Sec-Fetch-Site': 'cross-site'})
    assert client.get(f"/api/v1/assets/{base}/{model['modelId']}{suffix}").status_code == 404


def test_internal_viewer_escapes_supplier_metadata_and_exposes_no_storage_path(setup):
    context = setup(enabled=True, protocol=True)
    model = saved_mock_model(context, provider_id='OFFLINE-<img src=x onerror=alert(1)>')
    response = client_for(context).get(f"/api/v1/assets/internal-models/{model['modelId']}/viewer")
    assert response.status_code == 200
    assert '<img src=x onerror=' not in response.text and '&lt;img src=x onerror=alert(1)&gt;' in response.text
    assert str(context.assets.root) not in response.text
    assert FAKE_KEY not in response.text and FAKE_ADMIN not in response.text
