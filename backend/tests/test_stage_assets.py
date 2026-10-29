"""Offline stage delivery tests: only isolated files; no real Runtime or DB.

Run alone with --noconftest because these tests do not construct the production
application. The project's full isolated runner can also include this module.
"""
import hashlib
import json
import struct
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.app.errors import ServiceError
from backend.app.stage_assets import MAX_MANIFEST_BYTES, StageAssets, register_stage


def glb(payload=b'    '):
    return struct.pack('<4sII', b'glTF', 2, 20 + len(payload)) + struct.pack('<II', len(payload), 0x4e4f534a) + payload


def record(root, name, filename, raw=None, **extra):
    raw = glb() if raw is None else raw
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {'id': name, 'name': name, 'file': filename, 'sizeBytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), **extra}


@pytest.fixture
def resources(tmp_path):
    root = tmp_path / 'prepared-assets'
    root.mkdir()
    stage = record(root, 'stage-main', 'stage.glb', floorY=1.1,
                   camera={'position': [0, 2, 8], 'target': [0, 1, 0], 'fov': 45})
    person = record(root, 'duliniang', 'characters/duliniang.glb',
                    groupId='unclassified', description='用户命名角色，静态展示。',
                    question='想了解这个角色。', position=[0, 1, 0], scale=1.0,
                    citations=[{'id': 'source-1', 'title': '明确测试来源',
                                'url': 'https://example.org/source', 'excerpt': '显式测试夹具。'}])
    body = {'schemaVersion': '1.0', 'version': 'offline-stage-v1', 'stage': stage,
            'characters': [person], 'groups': [{'id': 'unclassified', 'name': '待分类'}]}
    (root / 'manifest.json').write_text(json.dumps(body), encoding='utf-8')
    return root, body


def rewrite(root, body):
    (root / 'manifest.json').write_text(json.dumps(body), encoding='utf-8')


def client(root, peer='127.0.0.1', host='127.0.0.1', headers=None):
    app = FastAPI()

    @app.exception_handler(ServiceError)
    async def fail(request: Request, error):
        return JSONResponse(error.public('offline-test'), status_code=error.status)

    register_stage(app, root)
    return TestClient(app, base_url=f'http://{host}', client=(peer, 12345), headers=headers)


def file_hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


def test_missing_root_never_creates_directory_or_manifest(tmp_path):
    root = tmp_path / 'missing' / 'assets'
    response = client(root).get('/api/v1/stage/catalog')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'STAGE_RESOURCES_UNAVAILABLE'
    assert not root.exists() and not root.parent.exists()


def test_catalog_uses_only_real_validated_files_and_safe_fields(resources):
    root, body = resources
    body['stage']['storageSecret'] = str(root)
    body['characters'][0]['fileSystemPath'] = str(root)
    rewrite(root, body)
    before = file_hashes(root)
    response = client(root).get('/api/v1/stage/catalog')
    assert response.status_code == 200
    data = response.json()
    assert data['stage']['available'] is True and data['stage']['status'] == 'ready'
    assert data['characters'][0]['groupId'] == 'unclassified'
    assert data['characters'][0]['fileUrl'] == '/api/v1/stage/files/duliniang'
    assert data['stage']['camera'] == body['stage']['camera']
    assert data['characters'][0]['citations'][0]['url'] == 'https://example.org/source'
    assert 'file' not in data['stage'] and str(root) not in response.text
    assert 'storageSecret' not in response.text and 'fileSystemPath' not in response.text
    assert file_hashes(root) == before


@pytest.mark.parametrize('peer,host,headers', [
    ('203.0.113.8', 'localhost', None), ('testclient', 'localhost', None),
    ('127.0.0.1', 'example.invalid', None),
    ('127.0.0.1', 'localhost', {'Sec-Fetch-Site': 'cross-site'}),
])
def test_local_access_is_required_for_both_routes(resources, peer, host, headers):
    root, _ = resources
    for path in ('/api/v1/stage/catalog', '/api/v1/stage/files/stage-main'):
        response = client(root, peer, host, headers).get(path)
        assert response.status_code == 404 and str(root) not in response.text


@pytest.mark.parametrize('host', ['localhost', '127.0.0.1'])
def test_glb_get_head_range_and_integrity_headers(resources, host):
    root, body = resources
    http = client(root, host=host)
    result = http.get('/api/v1/stage/files/stage-main')
    assert result.status_code == 200 and result.content == (root / 'stage.glb').read_bytes()
    assert result.headers['content-type'] == 'model/gltf-binary'
    assert result.headers['etag'] == '"' + body['stage']['sha256'] + '"'
    assert result.headers['cache-control'] == 'private, no-store'
    assert result.headers['x-content-type-options'] == 'nosniff'
    head = http.head('/api/v1/stage/files/stage-main')
    assert head.status_code == 200 and not head.content
    ranged = http.get('/api/v1/stage/files/stage-main', headers={'Range': 'bytes=0-3'})
    assert ranged.status_code == 206 and ranged.content == b'glTF'


def test_missing_character_is_unavailable_not_a_substitute_model(resources):
    root, _ = resources
    (root / 'characters/duliniang.glb').unlink()
    result = client(root).get('/api/v1/stage/catalog')
    assert result.status_code == 200
    assert result.json()['stage']['available'] is True
    person = result.json()['characters'][0]
    assert person['id'] == 'duliniang' and person['available'] is False and person['status'] == 'missing'
    assert client(root).get('/api/v1/stage/files/duliniang').status_code == 404
    assert not (root / 'characters/duliniang.glb').exists()


def test_wrong_size_or_checksum_never_delivers_as_ready(resources):
    root, body = resources
    service = StageAssets(root)
    assert service.catalog()['stage']['available']
    original = (root / 'stage.glb').read_bytes()
    (root / 'stage.glb').write_bytes(original[:-1] + b'x')
    assert service.catalog()['stage']['status'] == 'integrity_error'
    with pytest.raises(ServiceError) as exc:
        service.file('stage-main')
    assert exc.value.status == 409
    (root / 'stage.glb').write_bytes(original + b'extra')
    result = client(root).get('/api/v1/stage/files/stage-main')
    assert result.status_code == 409
    assert result.json()['error']['code'] == 'STAGE_FILE_INTEGRITY_ERROR'
    assert (root / 'stage.glb').read_bytes() == original + b'extra'


def test_mismatched_glb_header_is_rejected_even_with_matching_sha(resources):
    root, body = resources
    raw = b'not a real glb at all!!'
    (root / 'stage.glb').write_bytes(raw)
    body['stage'].update(sizeBytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    rewrite(root, body)
    assert client(root).get('/api/v1/stage/catalog').json()['stage']['status'] == 'integrity_error'
    assert client(root).get('/api/v1/stage/files/stage-main').status_code == 409


@pytest.mark.parametrize('value', ['../secret.glb', '/secret.glb', 'C:/private.glb',
                                   'https://example.org/a.glb', 'x\\secret.glb',
                                   'characters/../secret.glb', 'a.glb?token=x', 'a.glb#x'])
def test_manifest_cannot_select_arbitrary_paths(resources, value):
    root, body = resources
    body['stage']['file'] = value
    rewrite(root, body)
    before = file_hashes(root)
    response = client(root).get('/api/v1/stage/catalog')
    assert response.status_code == 503 and str(root) not in response.text
    assert file_hashes(root) == before


@pytest.mark.parametrize('mutation', [
    lambda body: body.update(schemaVersion='wrong'),
    lambda body: body['stage'].update(sha256='fake'),
    lambda body: body['stage'].update(sizeBytes=True),
    lambda body: body['characters'][0].update(id='stage-main'),
    lambda body: body['characters'][0].update(scale=float('nan')),
    lambda body: body['characters'][0].update(citations=[{'url': 'javascript:alert(1)'}]),
])
def test_invalid_manifest_data_is_safely_reported(resources, mutation):
    root, body = resources
    mutation(body)
    rewrite(root, body)
    result = client(root).get('/api/v1/stage/catalog')
    assert result.status_code == 503 and str(root) not in result.text


def test_invalid_json_and_oversized_manifest_are_not_rebuilt(resources):
    root, _ = resources
    for raw in (b'{bad json', b' ' * (MAX_MANIFEST_BYTES + 1)):
        (root / 'manifest.json').write_bytes(raw)
        assert client(root).get('/api/v1/stage/catalog').status_code == 503
        assert (root / 'manifest.json').read_bytes() == raw


def test_unknown_identifier_and_post_do_not_select_other_files(resources):
    root, _ = resources
    http = client(root)
    before = file_hashes(root)
    assert http.get('/api/v1/stage/files/not-in-manifest').status_code == 404
    assert http.get('/api/v1/stage/files/manifest.json').status_code == 404
    assert http.post('/api/v1/stage/catalog', json={}).status_code == 405
    assert http.post('/api/v1/stage/files/stage-main', json={}).status_code == 405
    assert file_hashes(root) == before


def test_existing_image_can_be_served_from_optional_media_list(resources):
    root, body = resources
    image = record(root, 'stage-thumb', 'thumb.png', b'\x89PNG\r\n\x1a\nfixture-pixels')
    body['media'] = [image]
    rewrite(root, body)
    result = client(root).get('/api/v1/stage/files/stage-thumb')
    assert result.status_code == 200 and result.headers['content-type'] == 'image/png'


def test_resolved_symlink_target_cannot_escape_storage_explicit_mock(resources, tmp_path, monkeypatch):
    # Deterministic resolve-layer double; not evidence of Windows ACL/symlink
    # permissions. Production separately rejects actual reparse/symlink flags.
    root, _ = resources
    target = tmp_path / 'outside.glb'
    target.write_bytes(glb())
    original = Path.resolve

    def resolve(path, *args, **kwargs):
        return target if path.name == 'escaped.glb' else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'resolve', resolve)
    with pytest.raises(ServiceError):
        StageAssets(root)._safe_path('escaped.glb')
    assert target.read_bytes() == glb()
