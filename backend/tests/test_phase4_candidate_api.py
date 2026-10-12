"""OFFLINE read-only candidate HTTP tests; no real catalog or supplier calls."""
import hashlib

import pytest

from backend.app.assets.candidates import CandidateCatalog
from backend.tests.test_phase4_assets import api, service, image_bytes


def register(catalog, raw=None, **extras):
    args = {'raw': image_bytes() if raw is None else raw, 'mime': 'image/png',
            'scope': 'offline-first-chibi-validation', 'sourceNote': '离线来源声明（未核实）',
            'licenseNote': '离线许可声明（未核实）',
            'promptSnapshot': {'version': 'offline_candidate_v1', 'text': '离线候选Prompt，非正式批准。'},
            'sourcePathLabel': 'D:\\private-test-only\\source.png'}
    return catalog.register(**{**args, **extras})


def setup_candidate(tmp_path, **extras):
    svc, _ = service(tmp_path)
    catalog = CandidateCatalog(svc)
    candidate = register(catalog, **extras)
    return svc, catalog, candidate, api(svc)


def candidate_url(candidate, suffix=''):
    return f"/api/v1/assets/candidates/{candidate['candidateId']}" + suffix


def test_metadata_not_a_confirmed_role_or_model_input(tmp_path):
    svc, catalog, candidate, client = setup_candidate(tmp_path)
    response = client.get(candidate_url(candidate))
    assert response.status_code == 200
    body = response.json()
    assert body['candidateId'] == candidate['candidateId']
    assert body['version'] == 1 and body['styleMode'] == 'chibi'
    assert body['accepted'] is body['imageAccepted'] is body['modelEligible'] is False
    assert body['characterId'] is body['assetId'] is body['sourceTaskId'] is None
    assert body['promptSnapshot']['frozenForReview'] is True
    assert body['promptSnapshot']['approved'] is False
    assert body['hash'] == candidate['hash']
    assert svc.usage is None and svc.model_service is None
    assert catalog.list() == [candidate]


def test_private_snapshot_paths_not_exposed_by_metadata_or_html(tmp_path):
    _, _, candidate, client = setup_candidate(tmp_path)
    metadata = client.get(candidate_url(candidate))
    preview = client.get(candidate_url(candidate, '/preview'))
    assert metadata.status_code == preview.status_code == 200
    for response in (metadata, preview):
        for forbidden in ('private-test-only', 'sourcePathLabel', 'originalStorageKey',
                          'candidate-originals/', 'historicalMetadata', 'catalog.sqlite3'):
            assert forbidden not in response.text
    assert 'storageKey' not in metadata.json()


def test_candidate_png_served_no_store_and_strict_hash_etag(tmp_path):
    _, catalog, candidate, client = setup_candidate(tmp_path)
    response = client.get(candidate_url(candidate, '/file'))
    assert response.status_code == 200
    assert response.headers['content-type'].split(';')[0] == 'image/png'
    assert response.headers['x-content-type-options'] == 'nosniff'
    cache = response.headers['cache-control']
    assert 'private' in cache and 'no-store' in cache
    assert response.headers['etag'].strip('"') == candidate['hash']
    assert hashlib.sha256(response.content).hexdigest() == candidate['hash']
    assert response.content == catalog.file_path(candidate['candidateId']).read_bytes()


def test_source_path_replacement_cannot_change_registered_candidate_file(tmp_path):
    source_path = tmp_path / 'same-original-path.png'
    old_source = image_bytes()
    source_path.write_bytes(old_source)
    _, _, first, client = setup_candidate(tmp_path, raw=source_path.read_bytes(), sourcePathLabel=str(source_path))
    response_before = client.get(candidate_url(first, '/file'))
    source_path.write_bytes(image_bytes(mode='RGBA'))
    response_after = client.get(candidate_url(first, '/file'))
    assert response_before.status_code == response_after.status_code == 200
    assert response_after.content == response_before.content
    assert response_after.headers['etag'] == response_before.headers['etag']
    assert hashlib.sha256(response_after.content).hexdigest() == first['hash']


def test_new_image_has_distinct_candidate_id_hash_and_preview_url(tmp_path):
    svc, catalog, first, client = setup_candidate(tmp_path)
    second = register(catalog, image_bytes(mode='RGBA'))
    assert first['candidateId'] != second['candidateId']
    assert first['hash'] != second['hash']
    assert second['version'] == first['version'] + 1
    for item in (first, second):
        file_response = client.get(candidate_url(item, '/file'))
        preview = client.get(candidate_url(item, '/preview'))
        assert file_response.status_code == preview.status_code == 200
        assert candidate_url(item, '/file') in preview.text
        assert file_response.headers['etag'].strip('"') == item['hash']
    assert svc.usage is None and svc.model_service is None


def test_legacy_metadata_v1_exists_but_cannot_read_current_source_file(tmp_path):
    svc, _ = service(tmp_path)
    catalog = CandidateCatalog(svc)
    source_path = tmp_path / 'replaced-original.png'
    source_path.write_bytes(image_bytes())
    old = catalog.import_history({'sha256': '1' * 64, 'styleMode': 'chibi',
                                  'source': '离线历史来源', 'licenseStatement': '离线历史声明',
                                  'path': str(source_path), 'size': 10, 'width': 40, 'height': 64},
                                 'offline-first-chibi-validation')
    new = register(catalog, source_path.read_bytes(), sourcePathLabel=str(source_path))
    client = api(svc)
    metadata = client.get(candidate_url(old))
    assert metadata.status_code == 200
    assert metadata.json()['version'] == 1 and metadata.json()['filesAvailable'] is False
    assert 'path' not in metadata.json()
    old_file = client.get(candidate_url(old, '/file'))
    assert old_file.status_code == 404
    assert old_file.json()['error']['code'] == 'CANDIDATE_FILE_UNAVAILABLE'
    assert client.get(candidate_url(new, '/file')).status_code == 200
    assert new['version'] == 2


@pytest.mark.parametrize('route', ['/images/{id}', '/images/{id}/file',
                                   '/models/{id}', '/models/{id}/file', '/characters/{id}'])
def test_candidate_uuid_cannot_be_used_as_formal_asset_uuid(tmp_path, route):
    _, _, candidate, client = setup_candidate(tmp_path)
    response = client.get('/api/v1/assets' + route.format(id=candidate['candidateId']))
    assert response.status_code == 404


def test_review_html_escapes_source_license_and_prompt_no_scripts(tmp_path):
    source = '<script>alert("source")</script>'
    license_note = '<img src=x onerror=alert("license")>'
    prompt_text = '<svg onload=alert("prompt")><script>window.location="https://example.invalid"</script>'
    _, _, candidate, client = setup_candidate(tmp_path, sourceNote=source,
        licenseNote=license_note, promptSnapshot={'version': 'offline-v1', 'text': prompt_text})
    response = client.get(candidate_url(candidate, '/preview'))
    assert response.status_code == 200
    assert response.headers['content-type'].split(';')[0] == 'text/html'
    assert 'no-store' in response.headers['cache-control']
    assert "script-src 'none'" in response.headers['content-security-policy']
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert '<script' not in response.text.lower()
    assert '<svg onload=' not in response.text.lower()
    assert '<img src=x onerror=' not in response.text.lower()
    assert '&lt;script&gt;' in response.text
    assert '&lt;img' in response.text and '&lt;svg' in response.text
    assert candidate_url(candidate, '/file') in response.text


@pytest.mark.parametrize('suffix', ['', '/accept', '/create', '/promote', '/model-approval', '/model-task'])
def test_candidate_routes_have_no_mutating_or_paid_entry(tmp_path, suffix):
    svc, catalog, candidate, client = setup_candidate(tmp_path)
    response = client.post(candidate_url(candidate, suffix), json={'accepted': True,
                                                                  'imageHash': candidate['hash']})
    assert response.status_code in (404, 405)
    saved = catalog.get(candidate['candidateId'])
    assert saved['accepted'] is saved['modelEligible'] is False
    assert svc.usage is None and svc.model_service is None
    assert saved == candidate


def test_no_bulk_post_candidate_creation_route(tmp_path):
    svc, catalog, _, client = setup_candidate(tmp_path)
    response = client.post('/api/v1/assets/candidates', json={'sourceTaskId': 'forged', 'accepted': True})
    assert response.status_code in (404, 405)
    assert len(catalog.list()) == 1
    assert svc.usage is None and svc.model_service is None


@pytest.mark.parametrize('candidate_id', ['not-a-uuid', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'])
def test_invalid_or_unknown_uuid_is_safe_error(tmp_path, candidate_id):
    svc, _ = service(tmp_path)
    client = api(svc)
    for suffix in ('', '/file', '/preview'):
        response = client.get('/api/v1/assets/candidates/' + candidate_id + suffix)
        assert response.status_code in (404, 422)
        assert 'Traceback' not in response.text and 'catalog.sqlite3' not in response.text


def test_changed_hash_snapshot_yields_error_instead_of_stale_preview(tmp_path):
    _, catalog, candidate, client = setup_candidate(tmp_path)
    path = catalog.file_path(candidate['candidateId'])
    altered = bytearray(path.read_bytes())
    altered[-1] ^= 1
    path.write_bytes(altered)
    response = client.get(candidate_url(candidate, '/file'))
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'CANDIDATE_FILE_CHANGED'
