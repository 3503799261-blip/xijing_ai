"""OFFLINE local texture recovery tests; no private models, ledger or API calls.

The source hash is patched ONLY for original synthetic tetrahedron fixtures.
The production utility still accepts one fixed supplier result hash.
"""
import ast
import hashlib
import inspect
import io
import socket
import struct

import httpx
import pytest
from PIL import Image

from backend.app.assets import validation
from backend.app.errors import ServiceError
from backend.app.providers.neural4d import Neural4DProvider
from backend.scripts import normalize_first_recovered_glb as recovery
from backend.tests.test_phase4_assets import image_bytes, parse_glb, textured_glb


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Offline texture recovery attempted network or supplier operations.')
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(httpx.AsyncClient, 'request', denied)
    monkeypatch.setattr(Neural4DProvider, 'create_once', denied)
    monkeypatch.setattr(Neural4DProvider, 'read_operation', denied)


@pytest.fixture(scope='module')
def offline_original():
    # Actual JPEG bytes with the same narrow format discrepancy diagnosed in
    # the supplier model; geometry remains the original four-face fixture.
    texture = image_bytes(size=(4096, 4096), fmt='JPEG')
    return textured_glb([texture, texture], fmt='JPEG', mime='image/jpg')


def split_glb(raw):
    json_size = struct.unpack_from('<I', raw, 12)[0]
    binary_size = struct.unpack_from('<I', raw, 20 + json_size)[0]
    start = 28 + json_size
    return parse_glb(raw), raw[start:start + binary_size]


def bind_offline_source(monkeypatch, raw):
    digest = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(recovery, 'ORIGINAL_HASH', digest)
    return digest


def test_local_conversion_rejects_unbound_source_hash_before_decode(monkeypatch):
    def no_decode(*args, **kwargs):
        raise AssertionError('Source mismatch must be rejected before image parsing.')
    monkeypatch.setattr(recovery.Image, 'open', no_decode)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(b'offline-wrong-source')


def test_fixed_offline_source_converts_only_textures_and_preserves_geometry(offline_original, monkeypatch):
    source_hash = bind_offline_source(monkeypatch, offline_original)
    source_doc, source_binary = split_glb(offline_original)
    converted, provenance = recovery.normalize_original(offline_original)
    result_doc, result_binary = split_glb(converted)
    checked = validation.validate_glb(converted)

    assert checked['valid'] is True and checked['selfContained'] is True
    assert checked['vertexCount'] == 4 and checked['triangleCount'] == 4
    assert checked['imageCount'] == 2 and checked['decodedTexturePixels'] == 2 * 2048 * 2048
    assert checked['decodedTexturePixels'] <= validation.MAX_TOTAL_TEXTURE_PIXELS
    assert 2048 * 2048 <= validation.MAX_TEXTURE_PIXELS
    assert {image['mimeType'] for image in result_doc['images']} == {'image/jpeg'}
    for image in result_doc['images']:
        view = result_doc['bufferViews'][image['bufferView']]
        start = view['byteOffset']
        with Image.open(io.BytesIO(result_binary[start:start + view['byteLength']])) as decoded:
            assert decoded.format == 'JPEG' and decoded.size == (2048, 2048)
            decoded.load()
    image_views = {image['bufferView'] for image in source_doc['images']}
    for index, source_view in enumerate(source_doc['bufferViews']):
        if index in image_views:
            continue
        result_view = result_doc['bufferViews'][index]
        old_start = source_view.get('byteOffset', 0)
        new_start = result_view['byteOffset']
        assert result_view['byteLength'] == source_view['byteLength']
        assert (source_binary[old_start:old_start + source_view['byteLength']]
                == result_binary[new_start:new_start + result_view['byteLength']])
    # Preserve complete scene/accessor/material semantics. Only image MIME and
    # the resource-buffer offsets/lengths are allowed to change.
    for key in source_doc.keys() - {'buffers', 'bufferViews', 'images'}:
        assert result_doc[key] == source_doc[key]
    assert provenance['supplierOriginalHash'] == source_hash
    assert provenance['derivedHash'] == checked['hash']
    assert provenance['geometryUnchanged'] is True and provenance['textureOnlyOptimization'] is True
    assert provenance['providerCalls'] == 0 and provenance['newGeneration'] is False
    assert hashlib.sha256(offline_original).hexdigest() == source_hash
    assert all(view['bytesUnchanged'] for view in provenance['geometryBufferViews'])


def test_local_conversion_requires_exact_diagnosed_texture_count(monkeypatch):
    single = textured_glb([image_bytes(size=(4096, 4096), fmt='JPEG')], fmt='JPEG', mime='image/jpg')
    bind_offline_source(monkeypatch, single)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(single)


def test_local_conversion_requires_diagnosed_texture_dimensions(monkeypatch):
    small = image_bytes(size=(64, 64), fmt='JPEG')
    source = textured_glb([small, small], fmt='JPEG', mime='image/jpg')
    bind_offline_source(monkeypatch, source)
    with pytest.raises(ServiceError, match='RECOVERY_SOURCE_MISMATCH'):
        recovery.normalize_original(source)


def test_local_conversion_has_no_network_or_creation_call_path(offline_original, monkeypatch):
    bind_offline_source(monkeypatch, offline_original)
    converted, provenance = recovery.normalize_original(offline_original)
    assert provenance['providerCalls'] == 0 and converted.startswith(b'glTF')
    # Whole utility uses the recovery-only service solely for its exclusive
    # owner lock and immutable frozen approval. No query/send method is called.
    tree = ast.parse(inspect.getsource(recovery))
    prohibited = {'submit', 'create_once', 'read_operation', 'refresh', 'verify',
                  'post', 'request', 'download', 'secure_download',
                  'connect_tcp', 'create_connection', 'getaddrinfo'}
    call_names = {node.func.attr for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not call_names.intersection(prohibited)
    assert 'RecoveryOnlyService' in {node.func.id for node in ast.walk(tree)
                                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}

