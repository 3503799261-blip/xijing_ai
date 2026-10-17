"""OFFLINE SECOND recovery regression: original synthetic geometry only.

Production IDs/hashes remain fixed. Tests patch them only inside isolated
fixtures and refuse DNS, HTTP and every provider operation. No private model,
project quota ledger or real API is opened by these tests.
"""
import ast
import asyncio
import hashlib
import inspect
import io
import json
import socket
import struct

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr

from backend.app.agents.store import TaskStore
from backend.app.assets.neural_service import ModelService
from backend.app.assets.service import AssetService
from backend.app.assets.usage import UsageManager
from backend.app.assets.validation import validate_glb
from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.providers.neural4d import Neural4DProvider
from backend.scripts import normalize_second_recovered_glb as recovery
from backend.tests.test_phase4_assets import asset, glb, image_bytes, parse_glb


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Offline second recovery attempted network/provider operations.')
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(httpx.AsyncClient, 'request', denied)
    for method in ('create_once', 'read_operation', 'download'):
        monkeypatch.setattr(Neural4DProvider, method, denied)


def split_glb(raw):
    json_size = struct.unpack_from('<I', raw, 12)[0]
    bin_size = struct.unpack_from('<I', raw, 20 + json_size)[0]
    return parse_glb(raw), raw[28 + json_size:28 + json_size + bin_size]


def original_fixture(*, size=(4096, 4096), fmt='JPEG', mime='image/jpg'):
    """Four-face tetrahedron with a real UV view and two self-contained images."""
    doc, binary = split_glb(glb())
    binary = bytearray(binary)
    uv = struct.pack('<8f', 0, 0, 1, 0, 1, 1, 0, 1)
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(uv)})
    binary.extend(uv)
    doc['accessors'].append({'bufferView': 2, 'componentType': 5126, 'count': 4, 'type': 'VEC2'})
    doc['meshes'][0]['primitives'][0]['attributes']['TEXCOORD_0'] = 2
    doc.update(images=[], textures=[], samplers=[{'magFilter': 9729, 'minFilter': 9987}])
    texture = image_bytes(size=size, fmt=fmt)
    for _ in range(2):
        view_id = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(texture)})
        binary.extend(texture)
        binary.extend(b'\0' * (-len(binary) % 4))
        doc['images'].append({'bufferView': view_id, 'mimeType': mime})
        doc['textures'].append({'source': len(doc['images']) - 1, 'sampler': 0})
    doc['materials'] = [{'pbrMetallicRoughness': {'baseColorTexture': {'index': 0, 'texCoord': 0}},
                         'normalTexture': {'index': 1, 'texCoord': 0}}]
    doc['meshes'][0]['primitives'][0]['material'] = 0
    doc['buffers'][0]['byteLength'] = len(binary)
    return glb(doc, bytes(binary))


@pytest.fixture(scope='module')
def offline_original():
    return original_fixture()


def bind_source(monkeypatch, raw):
    digest = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(recovery, 'ORIGINAL_HASH', digest)
    monkeypatch.setattr(recovery, 'ORIGINAL_SIZE', len(raw))
    return digest


def test_unbound_source_rejected_before_decode(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Unbound original must be rejected before decode.')
    monkeypatch.setattr(recovery.Image, 'open', denied)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(b'not-the-fixed-original')


def test_fixed_original_must_also_match_length(offline_original, monkeypatch):
    bind_source(monkeypatch, offline_original)
    monkeypatch.setattr(recovery, 'ORIGINAL_SIZE', len(offline_original) + 1)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(offline_original)


def test_only_mime_and_textures_change_geometry_uv_and_semantics_preserved(offline_original, monkeypatch):
    original_hash = bind_source(monkeypatch, offline_original)
    source_doc, source_binary = split_glb(offline_original)
    converted, provenance = recovery.normalize_original(offline_original)
    result_doc, result_binary = split_glb(converted)
    checked = validate_glb(converted)
    assert checked['valid'] and checked['triangleCount'] == 4 and checked['vertexCount'] == 4
    assert checked['imageCount'] == 2 and checked['decodedTexturePixels'] == 2 * 2048 * 2048
    for number in (0, 1, 2):
        old, new = source_doc['bufferViews'][number], result_doc['bufferViews'][number]
        before = source_binary[old['byteOffset']:old['byteOffset'] + old['byteLength']]
        after = result_binary[new['byteOffset']:new['byteOffset'] + new['byteLength']]
        assert before == after and hashlib.sha256(before).hexdigest() == provenance['geometryBufferViews'][number]['derivedHash']
    for image in result_doc['images']:
        assert image['mimeType'] == 'image/jpeg'
        view = result_doc['bufferViews'][image['bufferView']]
        raw = result_binary[view['byteOffset']:view['byteOffset'] + view['byteLength']]
        with Image.open(io.BytesIO(raw)) as decoded:
            assert decoded.format == 'JPEG' and decoded.size == (2048, 2048)
            decoded.load()
    for key in source_doc.keys() - {'buffers', 'bufferViews', 'images'}:
        assert source_doc[key] == result_doc[key]
    assert provenance['supplierOriginalHash'] == original_hash
    assert provenance['geometryUnchanged'] and provenance['sceneNodeAccessorMaterialSemanticsUnchanged']
    assert provenance['providerCalls'] == 0 and provenance['newGeneration'] is False
    assert hashlib.sha256(offline_original).hexdigest() == original_hash


@pytest.mark.parametrize('size,fmt,mime', [
    ((64, 64), 'JPEG', 'image/jpg'),
    ((4096, 4096), 'PNG', 'image/jpg'),
    ((4096, 4096), 'JPEG', 'image/jpeg'),
])
def test_narrow_diagnosed_image_conditions_required(size, fmt, mime, monkeypatch):
    raw = original_fixture(size=size, fmt=fmt, mime=mime)
    bind_source(monkeypatch, raw)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(raw)


def test_fixed_view_layout_required(offline_original, monkeypatch):
    doc, binary = split_glb(offline_original)
    doc['images'][0]['bufferView'] = 2
    raw = glb(doc, binary)
    bind_source(monkeypatch, raw)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(raw)


@pytest.mark.parametrize('method', ['approve', 'approve_technical_candidate', 'submit', 'verify', 'refresh'])
def test_local_service_refuses_all_network_and_approval_methods(method):
    service = recovery.LocalOnlyModelService.__new__(recovery.LocalOnlyModelService)
    with pytest.raises(ServiceError, match='LOCAL_RECOVERY_NETWORK_FORBIDDEN'):
        result = getattr(service, method)({'irrelevant': 'fixture'})
        if inspect.isawaitable(result):
            asyncio.run(result)


def test_utility_has_no_network_or_creation_calls():
    tree = ast.parse(inspect.getsource(recovery))
    names = {node.func.attr for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not names.intersection({'submit', 'create_once', 'read_operation', 'refresh', 'verify',
        'post', 'request', 'download', 'secure_download', 'connect_tcp', 'getaddrinfo', 'create_connection'})
    assert 'freeze' in names and 'verify_character_snapshot' in names


def test_offline_registration_uses_formal_lineage_and_preserves_global_count(tmp_path, monkeypatch, offline_original):
    settings = Settings(_env_file=None, rag_data_dir=tmp_path / 'runtime',
        neural4d_generation_enabled=False, neural4d_protocol_verified=False,
        neural4d_api_key=SecretStr(''), deepseek_api_key=SecretStr(''))
    tasks = TaskStore(settings.rag_data_dir / 'agent-tasks.sqlite3')
    assets = AssetService(settings, tasks)
    created = asset(assets, tasks, purpose='比赛主展示', styleMode='realistic')
    assets.approve_visual(created['assetId'], created['visualPrompt']['promptHash'])
    image = assets.upload_image(created['assetId'], image_bytes(), 'image/png', 'manual_image', '仅原创离线测试图片')
    image = assets.accept_image(image['imageId'], image['hash'])
    usage = UsageManager(tmp_path / '.runtime/neural4d-usage.sqlite3')
    usage.initialize_history(0, '仅离线测试的历史，不是真实项目额度。')
    first = {'modelCount': 1, 'fixture': 'first'}
    approval = usage.approve(first, '仅离线第一模型', True, 30)
    prior = usage.reserve('offline-first', approval['approvalId'], first, '仅离线第一模型', True, True)
    usage.mark_started(prior['attemptId'])
    usage.finish(prior['attemptId'], 'SUCCEEDED', provider_task_id='offline-first-task')

    def no_request(*args, **kwargs):
        raise AssertionError('Purely local recovery reached an HTTP transport.')

    class OfflineLocalService(recovery.LocalOnlyModelService):
        def __init__(self, settings, assets, usage):
            ModelService.__init__(self, settings, assets, usage, httpx.MockTransport(no_request))

    local = OfflineLocalService(settings, assets, usage)
    payload = local.freeze({'assetId': created['assetId'], 'assetVersion': 1,
        'imageId': image['imageId'], 'imageHash': image['hash'],
        'promptHash': created['visualPrompt']['promptHash'], 'purpose': '比赛主展示', 'modelCount': 1})
    approval = usage.approve(payload, '比赛主展示', True, 30)
    with assets.store.connect() as db:
        db.execute('INSERT INTO neural4d_frozen_approvals VALUES (?,?)',
                   (approval['approvalId'], json.dumps(payload, ensure_ascii=False, sort_keys=True)))
    second = usage.reserve('offline-second', approval['approvalId'], payload, '比赛主展示', True, True)
    usage.mark_started(second['attemptId'])
    usage.finish(second['attemptId'], 'PENDING_RECONCILIATION', provider_task_id='offline-second-task', error_code='MODEL_TEXTURE_INVALID')
    digest = bind_source(monkeypatch, offline_original)
    key = assets.save_bytes('recovery-quarantine', offline_original, digest, 'bin')
    for name, value in {'Settings': lambda: settings, 'WORKSPACE_ROOT': tmp_path,
            'LocalOnlyModelService': OfflineLocalService, 'JOB_ID': second['attemptId'],
            'TASK_ID': 'offline-second-task', 'ASSET_ID': created['assetId'], 'IMAGE_ID': image['imageId'],
            'AGENT_TASK_ID': created['sourceTaskId'], 'IMAGE_HASH': image['hash'],
            'SOURCE_IMAGE_HASH': image['sourceHash']}.items():
        monkeypatch.setattr(recovery, name, value)
    before = usage.summary()
    record = {}
    recovery.run(record)
    assert record['outcome'] == 'LOCAL_RECOVERY_VALIDATED'
    assert record['creationAttemptsUnchanged'] and record['realHttpRequestsUnchanged']
    assert record['usageAfter']['occupied_attempts'] == before['occupied_attempts'] == 2
    assert record['usageAfter']['remaining_attempts'] == 1
    assert record['model']['assetId'] == created['assetId'] and record['model']['imageId'] == image['imageId']
    assert record['model']['origin'] == 'neural4d' and record['model']['providerTaskId'] == 'offline-second-task'
    assert (assets.root / key).read_bytes() == offline_original
    provenance_raw = (assets.root / record['provenanceStorageKey']).read_bytes()
    assert hashlib.sha256(provenance_raw).hexdigest() == record['provenanceHash']
    assert json.loads(provenance_raw)['sourceResultHash'] == created['sourceResultHash']
    assert usage.get_attempt(second['attemptId'])['state'] == 'SUCCEEDED'
    # Re-entry is an idempotent local read/registration, never another model.
    repeated = {}
    recovery.run(repeated)
    assert repeated['model']['modelId'] == record['model']['modelId']
    assert usage.summary()['occupied_attempts'] == 2 and usage.summary()['realHttpRequests'] == 0
