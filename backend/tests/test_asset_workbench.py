"""OFFLINE asset-workbench discovery: temporary catalogs and original geometry.

These are read-only API tests, not evidence of a generated opera model or a
supplier call. No production configuration, catalog or quota ledger is used.
"""
import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.tests.test_phase4_assets import api, asset, glb, service


@pytest.fixture
def workbench(tmp_path):
    assets, tasks = service(tmp_path)
    character = asset(assets, tasks, styleMode='realistic')
    public = assets.import_model(character['assetId'], glb(), 'OFFLINE original test geometry')
    fixture = assets.register_fixture(glb(), 'OFFLINE original fixture geometry')
    # This synthetic catalog entry exercises the existing private identity. It
    # never executes an approval, model service, provider, or generation task.
    private = assets.store.add_file('model', None, {
        'hash': fixture['hash'], 'size': fixture['size'], 'format': 'glb',
        'origin': 'neural4d_technical_test', 'assetKind': 'internal_technical_test',
        'title': 'OFFLINE private model identity', 'licenseNote': 'OFFLINE test only',
        'validation': fixture['validation'], 'visibility': 'internal',
        'internalUseOnly': True, 'publicationAllowed': False,
        'cultureAlignmentVerified': False, 'characterId': None,
        'styleMode': 'chibi', 'styleVersion': None,
        'candidateId': str(uuid.uuid4()), 'promptHash': 'a' * 64,
        'storageKey': f"models/{fixture['hash']}.glb",
    })
    return assets, tasks, character, public, private


def client_for(assets, *, peer='127.0.0.1', host='127.0.0.1', headers=None):
    return TestClient(api(assets).app, base_url=f'http://{host}',
                      client=(peer, 50000), headers=headers)


def hashes(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


def test_default_and_explicit_false_keep_private_models_hidden(workbench):
    assets, _, _, public, private = workbench
    for suffix in ('', '?includeInternal=false'):
        response = client_for(assets).get('/api/v1/assets/models' + suffix)
        assert response.status_code == 200
        ids = {item['modelId'] for item in response.json()['models']}
        assert public['modelId'] in ids and private['modelId'] not in ids
    assert private['modelId'] not in {item['modelId'] for item in assets.list_models()}


@pytest.mark.parametrize('host', ['127.0.0.1', 'localhost'])
def test_loopback_workbench_can_discover_existing_private_model(workbench, host):
    assets, _, _, public, private = workbench
    response = client_for(assets, host=host).get('/api/v1/assets/models?includeInternal=true')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.json()['internalIncluded'] is True
    items = {item['modelId']: item for item in response.json()['models']}
    assert public['modelId'] in items
    assert items[private['modelId']] == assets.get_model(private['modelId'])
    assert items[private['modelId']]['assetId'] is None
    assert items[private['modelId']]['publicationAllowed'] is False
    assert items[private['modelId']]['cultureAlignmentVerified'] is False
    assert 'storageKey' not in response.text and str(assets.root) not in response.text


@pytest.mark.parametrize('peer,host,headers', [
    ('203.0.113.4', '127.0.0.1', None),
    ('127.0.0.1', 'example.invalid', None),
    ('testclient', 'localhost', None),
    ('127.0.0.1', 'localhost', {'Sec-Fetch-Site': 'cross-site'}),
])
def test_private_discovery_requires_existing_loopback_access_guard(workbench, peer, host, headers):
    assets, _, _, _, private = workbench
    response = client_for(assets, peer=peer, host=host, headers=headers).get(
        '/api/v1/assets/models?includeInternal=true')
    assert response.status_code == 404
    assert private['modelId'] not in response.text
    assert private['hash'] not in response.text
    assert 'models' not in response.json()


def test_access_guard_precedes_catalog_read(workbench, monkeypatch):
    assets, *_ = workbench
    def unexpected_read(*args, **kwargs):
        raise AssertionError('Unauthorized request reached model catalog')
    monkeypatch.setattr(assets, 'list_models', unexpected_read)
    response = client_for(assets, peer='203.0.113.4').get(
        '/api/v1/assets/models?includeInternal=true')
    assert response.status_code == 404


def test_character_filter_preserves_existing_asset_semantics(workbench):
    assets, _, character, public, private = workbench
    for include in (False, True):
        response = client_for(assets).get('/api/v1/assets/models', params={
            'assetId': character['assetId'], 'includeInternal': str(include).lower()})
        assert response.status_code == 200
        assert [item['modelId'] for item in response.json()['models']] == [public['modelId']]
        assert private['modelId'] not in response.text
    missing = client_for(assets).get('/api/v1/assets/models', params={
        'assetId': str(uuid.uuid4()), 'includeInternal': 'true'})
    assert missing.status_code == 404


def test_invalid_include_internal_boolean_is_rejected(workbench):
    assets, *_ = workbench
    response = client_for(assets).get('/api/v1/assets/models?includeInternal=not-a-boolean')
    assert response.status_code == 422


def test_discovery_preserves_catalog_tasks_and_files_without_initialization(workbench, tmp_path, monkeypatch):
    assets, tasks, character, _, private = workbench
    client = client_for(assets)
    before = hashes(tmp_path)
    catalog_before = assets.store.file('model', private['modelId'])
    tasks_before = (tasks.status(character['sourceTaskId']), tasks.result(character['sourceTaskId']))
    def no_initialization(*args, **kwargs):
        raise AssertionError('Read-only discovery must not initialize a database')
    monkeypatch.setattr('backend.app.assets.store.initialize_database', no_initialization)
    for _ in range(2):
        assert client.get('/api/v1/assets/models').status_code == 200
        assert client.get('/api/v1/assets/models?includeInternal=true').status_code == 200
    assert hashes(tmp_path) == before
    assert assets.store.file('model', private['modelId']) == catalog_before
    assert (tasks.status(character['sourceTaskId']), tasks.result(character['sourceTaskId'])) == tasks_before
    # The shared autouse fixture may seed its isolated quota ledger; the full
    # file inventory above proves discovery neither changes nor adds one.


def test_discovery_does_not_relax_private_file_or_metadata_access(workbench):
    assets, _, _, _, private = workbench
    for suffix in ('', '/file', '/download'):
        response = client_for(assets, peer='203.0.113.4').get(
            f"/api/v1/assets/models/{private['modelId']}{suffix}")
        assert response.status_code == 404
