"""Offline recovery guards; no real configuration, ledger or supplier calls."""
import asyncio
import hashlib
import json
from types import SimpleNamespace
import httpx
import pytest
from pydantic import SecretStr
from backend.app.errors import ServiceError
from backend.app.assets.service import AssetService
from backend.scripts.recover_first_internal_model import (
    OriginalTaskOnlyProvider, RecoveryOnlyService, JOB_ID, TASK_ID, cached_model)


def provider(tmp_path):
    calls, logs = [], []
    settings = SimpleNamespace(neural4d_api_key=SecretStr('offline-fixture-not-a-key'),
                               neural4d_timeout_seconds=2, neural4d_generation_enabled=False)
    usage = SimpleNamespace(path=tmp_path / 'offline.sqlite3', record_request=lambda *args, **kw: logs.append((args, kw)))
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'codeStatus': 0, 'modelUrl': 'https://example.invalid/test.glb?secret=OFFLINE_SECRET'})
    return OriginalTaskOnlyProvider(settings, usage, httpx.MockTransport(handler)), calls, logs


@pytest.mark.parametrize('method', ['approve', 'approve_technical_candidate', 'submit'])
def test_recovery_service_never_authorizes_or_submits(method):
    service = RecoveryOnlyService.__new__(RecoveryOnlyService)
    with pytest.raises(ServiceError, match='RECOVERY_CREATION_FORBIDDEN'):
        result = getattr(service, method)({'arbitrary': 'attempt'})
        if method == 'submit':
            asyncio.run(result)


def test_recovery_provider_has_no_creation_capability(tmp_path):
    obj, calls, logs = provider(tmp_path)
    with pytest.raises(ServiceError, match='RECOVERY_CREATION_FORBIDDEN'):
        asyncio.run(obj.create_once('wrong-attempt', b'not-an-image'))
    assert calls == [] and logs == []


@pytest.mark.parametrize('path,body,operation,job', [
    ('queryPointsInfo', {}, 'verify', JOB_ID),
    ('retrieveModel', {'uuid': 'another-task'}, 'query_model', JOB_ID),
    ('retrieveModel', {'uuid': TASK_ID}, 'query_model', 'another-job'),
    ('retrieveModel', {'uuid': TASK_ID}, 'create_model', JOB_ID),
    ('generateModelWithImage', {'uuid': TASK_ID}, 'query_model', JOB_ID),
])
def test_only_original_query_can_reach_mock_transport(tmp_path, path, body, operation, job):
    obj, calls, logs = provider(tmp_path)
    with pytest.raises(ServiceError, match='RECOVERY_SCOPE_INVALID'):
        asyncio.run(obj.read_operation(path, body, operation, attempt_id=job))
    assert calls == [] and logs == []


def test_original_query_only_records_structure_and_no_signed_value(tmp_path):
    obj, calls, logs = provider(tmp_path)
    result = asyncio.run(obj.read_operation('retrieveModel', {'uuid': TASK_ID}, 'query_model', attempt_id=JOB_ID))
    assert len(calls) == 1 and json.loads(calls[0].content) == {'uuid': TASK_ID}
    assert result['codeStatus'] == 0 and obj.last_result_shape == {'codeStatus': 'int', 'modelUrl': 'str'}
    assert 'OFFLINE_SECRET' not in json.dumps(obj.last_result_shape) + json.dumps(logs)
    assert logs[0][0] == ('query_model',) and logs[0][1]['attempt_id'] == JOB_ID


def cached_assets(tmp_path, *, provider_task_id=TASK_ID):
    """Local-only byte-integrity fixture; not a supplier or GLB-format test."""
    assets = AssetService(SimpleNamespace(rag_data_dir=tmp_path / 'offline-assets'), None)
    raw = b'offline-model-cache-fixture'
    digest = hashlib.sha256(raw).hexdigest()
    storage_key = assets.save_bytes('models', raw, digest, 'glb')
    model = assets.store.add_file('model', None, {
        'providerTaskId': provider_task_id, 'hash': digest, 'size': len(raw),
        'format': 'glb', 'storageKey': storage_key,
        'origin': 'neural4d_technical_test', 'visibility': 'internal',
        'internalUseOnly': True})
    return assets, model, assets.root / storage_key, raw


def test_cached_success_requires_record_for_exact_original_task(tmp_path, monkeypatch):
    assets, _, _, _ = cached_assets(tmp_path, provider_task_id='unrelated-offline-task')
    def forbidden(*args):
        raise AssertionError('Missing model must not be exposed as cached success.')
    monkeypatch.setattr(assets, 'public_model', forbidden)
    with pytest.raises(ServiceError, match='RECOVERY_MODEL_MISSING'):
        cached_model(assets)


def test_cached_success_checks_bytes_and_returns_public_metadata_only(tmp_path, monkeypatch):
    assets, model, path, raw = cached_assets(tmp_path)
    checked = []
    actual_file_path = assets.file_path
    def checked_path(kind, model_id):
        checked.append((kind, model_id))
        return actual_file_path(kind, model_id)
    monkeypatch.setattr(assets, 'file_path', checked_path)
    result = cached_model(assets)
    assert checked == [('model', model['modelId'])]
    assert result['hash'] == hashlib.sha256(raw).hexdigest()
    assert path.read_bytes() == raw
    assert result['providerTaskId'] == TASK_ID and result['internalUseOnly'] is True
    assert 'storageKey' not in result and str(path) not in json.dumps(result)


@pytest.mark.parametrize('damage,error_code', [
    ('missing', 'ASSET_FILE_UNAVAILABLE'),
    ('length', 'ASSET_FILE_CHANGED'),
    ('hash', 'ASSET_FILE_CHANGED'),
    ('storage_key', 'ASSET_STORAGE_INVALID'),
])
def test_cached_success_fails_closed_for_missing_or_changed_file(tmp_path, monkeypatch, damage, error_code):
    assets, model, path, raw = cached_assets(tmp_path)
    if damage == 'missing':
        # Only a temporary fixture created by this test is removed.
        path.unlink()
    elif damage == 'length':
        path.write_bytes(raw + b'changed')
    elif damage == 'hash':
        path.write_bytes(b'X' + raw[1:])
    else:
        model['storageKey'] = '../outside-offline-fixture.glb'
        with assets.store.connect() as db:
            db.execute('UPDATE asset_models SET content_json=? WHERE model_id=?',
                       (json.dumps(model), model['modelId']))
    def forbidden(*args):
        raise AssertionError('Invalid cached model must not be publicly rendered.')
    monkeypatch.setattr(assets, 'public_model', forbidden)
    with pytest.raises(ServiceError, match=error_code):
        cached_model(assets)
