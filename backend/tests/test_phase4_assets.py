"""OFFLINE only: synthetic TaskStore artifacts are never demonstration evidence."""
import copy
import hashlib
import io
import json
import struct
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
from backend.app.agents.store import TaskStore, AGENTS
from backend.app.agents.schemas import CharacterDesign, CultureReview
from backend.app.assets.service import AssetService
from backend.app.assets.schemas import CreateAsset, ModelApprovalRequest
from backend.app.assets.validation import normalize_image, validate_glb, MAX_IMAGE_BYTES
from backend.app.assets.visual_prompt import visual_prompt
from backend.app.api.assets import register_assets
from backend.app.errors import ServiceError


def fixture_result():
    """Explicitly synthetic schema contract; not real opera claims."""
    element = {'description': '仅离线结构测试元素', 'interpretation': 'evidence_based', 'evidenceIds': ['offline-evidence-1']}
    return {'schemaVersion': '1.0', 'design': {'schemaVersion': '1.0', 'name': '离线测试角色',
            'positioning': '仅供离线测试，不是文化知识', 'costume': [element],
            'colors': [{'description': '离线测试原创颜色', 'interpretation': 'creative', 'evidenceIds': []}],
            'visualElements': [element], 'creativeElements': [], 'visualPrompt': '仅离线舞台背景测试',
            'usedEvidenceIds': ['offline-evidence-1'], 'limitations': ['仅测试用途']},
            'review': {'verdict': 'pass', 'issues': [], 'suggestions': [],
                       'checkedEvidenceIds': ['offline-evidence-1'], 'needsHumanReview': True},
            'citations': [{'id': 'offline-evidence-1', 'title': '离线测试证据（非真实资料）', 'sourceId': 'offline-source',
                           'locator': 'fixture', 'url': 'https://example.invalid/offline', 'excerpt': '不是真实京剧资料。',
                           'contentKind': 'original_fact_summary'}], 'uncertain': False,
            'knowledgeGeneration': 'offline-fixture-v1', 'promptVersions': {'planner': 'test-only'},
            'confirmationReason': 'final_acceptance'}


def confirmed_export_regression():
    """Previously recorded data in a sanitized OFFLINE regression fixture.

    Its temporary TaskStore states in these tests are synthetic. They are not
    evidence of new real Agent execution, user approval or model generation.
    """
    return json.loads((Path(__file__).parent / 'fixtures' / 'phase4' /
                       'confirmed-character-export-regression.json').read_text(encoding='utf-8'))['result']


def task(store, *, confirmed=True, change=None):
    task_id, _ = store.create({'requirements': '仅离线测试', 'style': '京剧写意'}, 'fixture-' + str(len(store.path.name)) + '-' + __import__('uuid').uuid4().hex)
    store.start(task_id)
    for aid in AGENTS:
        store.emit(task_id, aid, 'running', '离线测试')
        store.emit(task_id, aid, 'completed', '离线测试', {'testDouble': True})
    result = fixture_result()
    if change:
        change(result)
    store.finish(task_id, result)
    if confirmed:
        current = store.status(task_id)
        store.confirm(task_id, current['confirmation']['id'], current['lastSequence'])
    return task_id


def service(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3', create=True)
    settings = SimpleNamespace(rag_data_dir=tmp_path / 'runtime')
    return AssetService(settings, store, create=True), store


def asset(svc, store, **extras):
    task_id = task(store)
    return svc.create_character({'sourceTaskId': task_id, 'mode': 'personal', 'purpose': '仅离线测试', **extras})


def image_bytes(mode='RGB', size=(32, 48), fmt='PNG'):
    stream = io.BytesIO()
    Image.new(mode, size, '#7e2440').save(stream, format=fmt)
    return stream.getvalue()


def glb(doc=None, binary=None):
    """Original procedural tetrahedron (4 triangles); no third party asset."""
    if binary is None:
        binary = struct.pack('<12f', -1, 0, -1, 1, 0, -1, 0, 0, 1, 0, 2, 0) + struct.pack('<12H', 0, 1, 2, 0, 3, 1, 1, 3, 2, 2, 3, 0)
    if doc is None:
        doc = {'asset': {'version': '2.0', 'generator': 'xijing offline original test geometry'},
               'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
               'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1}]}],
               'buffers': [{'byteLength': len(binary)}],
               'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 48}, {'buffer': 0, 'byteOffset': 48, 'byteLength': 24}],
               'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 4, 'type': 'VEC3', 'min': [-1, 0, -1], 'max': [1, 2, 1]},
                             {'bufferView': 1, 'componentType': 5123, 'count': 12, 'type': 'SCALAR'}]}
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    return struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(encoded) + 8 + len(binary)) + struct.pack('<II', len(encoded), 0x4e4f534a) + encoded + struct.pack('<II', len(binary), 0x004e4942) + binary


def parse_glb(raw):
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20+size])


def textured_glb(images=None, *, fmt='PNG', mime='image/png'):
    """Original offline geometry plus actual small self-contained raster data."""
    original = glb()
    doc = parse_glb(original)
    json_size = struct.unpack_from('<I', original, 12)[0]
    binary = bytearray(original[20 + json_size + 8:])
    images = images or [image_bytes(fmt=fmt)]
    doc.update(images=[], textures=[], samplers=[{'magFilter': 9729, 'minFilter': 9987}])
    for image in images:
        start = len(binary)
        binary.extend(image)
        view_id = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(image)})
        doc['images'].append({'mimeType': mime, 'bufferView': view_id})
        doc['textures'].append({'source': len(doc['images']) - 1, 'sampler': 0})
        binary.extend(b'\0' * (-len(binary) % 4))
    doc['materials'] = [{'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}}}]
    doc['meshes'][0]['primitives'][0]['material'] = 0
    doc['buffers'][0]['byteLength'] = len(binary)
    return glb(doc, bytes(binary))


def api(svc):
    app = FastAPI()
    @app.middleware('http')
    async def rid(request: Request, call_next):
        request.state.request_id = 'offline-request'
        return await call_next(request)
    @app.exception_handler(ServiceError)
    async def error(request, exc):
        return JSONResponse(exc.public(request.state.request_id), status_code=exc.status)
    register_assets(app, svc)
    return TestClient(app)


def test_snapshot_requires_authoritative_confirmation_and_preserves_phase3(tmp_path):
    svc, store = service(tmp_path)
    pending = task(store, confirmed=False)
    with pytest.raises(ServiceError, match='CHARACTER_NOT_CONFIRMED'):
        svc.create_character({'sourceTaskId': pending, 'purpose': '测试'})
    before = store.result(pending)
    current = store.status(pending)
    store.confirm(pending, current['confirmation']['id'], current['lastSequence'])
    created = svc.create_character({'sourceTaskId': pending, 'purpose': '测试'})
    assert created['sourceTaskId'] == pending and created['version'] == 1
    assert created['characterSnapshot'] == before['design']
    assert created['visualPrompt']['originalVisualPrompt'] == before['design']['visualPrompt']
    assert '简洁纯色背景' in created['visualPrompt']['imagePrompt']
    assert created['commercialRightsVerified'] is False
    assert created['images'] == created['models'] == []
    assert 'visualPrompt' not in store.result(pending)
    assert svc.create_character({'sourceTaskId': pending, 'purpose': '测试'})['assetId'] == created['assetId']
    reopened = AssetService(svc.settings, TaskStore(store.path))
    assert reopened.get_character(created['assetId'])['sourceResultHash'] == created['sourceResultHash']


def test_confirmed_phase3_export_trace_metadata_is_separated_without_relaxing_culture_schema(tmp_path):
    exported = confirmed_export_regression()
    assert exported['design']['name'] == '青旌将·霄羽'
    # Reproduce the real export-envelope failure before the asset adapter.
    for key, schema in [('design', CharacterDesign), ('review', CultureReview)]:
        with pytest.raises(ValidationError) as error:
            schema.model_validate(exported[key])
        assert [(item['loc'], item['type']) for item in error.value.errors()] == [(('execution',), 'extra_forbidden')]
    svc, store = service(tmp_path)
    source = task(store, change=lambda result: result.update(exported))
    before = store.result(source)
    assets = [svc.create_character({'sourceTaskId': source, 'purpose': '导出兼容离线回归', 'styleMode': mode})
              for mode in ('realistic', 'chibi')]
    for created in assets:
        expected_design = {key: value for key, value in before['design'].items() if key != 'execution'}
        expected_review = {key: value for key, value in before['review'].items() if key != 'execution'}
        assert created['characterSnapshot'] == expected_design
        assert created['reviewSnapshot'] == expected_review
        assert created['citationSnapshot'] == before['citations']
        assert not created['culturalReviewRequired']
        assert svc.verify_character_snapshot(created['assetId'])['sourceResultHash'] == created['sourceResultHash']
    assert assets[0]['characterId'] == assets[1]['characterId']
    assert store.result(source) == before


def test_confirmed_phase3_export_http_asset_registration_regression(tmp_path):
    svc, store = service(tmp_path)
    source = task(store, change=lambda result: result.update(confirmed_export_regression()))
    with api(svc) as client:
        result = client.post('/api/v1/assets/characters',
                             json={'sourceTaskId': source, 'purpose': '导出兼容HTTP离线回归', 'styleMode': 'chibi'})
        assert result.status_code == 201
        assert result.json()['name'] == '青旌将·霄羽' and result.json()['styleMode'] == 'chibi'
        assert 'execution' not in result.json()['characterSnapshot']
        assert 'execution' not in result.json()['reviewSnapshot']
        assert 'redacted-phase3' not in result.text


@pytest.mark.parametrize('change', [
    lambda r: r['design'].update(unrecognizedCultureProperty='blocked'),
    lambda r: r['review'].update(unrecognizedCultureProperty='blocked'),
    lambda r: r['design']['costume'][0].update(unrecognizedCultureProperty='blocked'),
    lambda r: r['design']['execution'].update(unrecognizedTraceProperty='blocked'),
    lambda r: r['review']['execution']['usage'].update(unrecognizedUsageProperty=1),
    lambda r: r['design']['execution']['usage'].update(prompt_tokens=True),
    lambda r: r['review']['execution'].update(promptVersion='agent_designer_v1'),
    lambda r: r['review'].update(programmaticChecks={'garmentReferenceGuard': 'conservative_literal_absence',
                                                    'issuesFound': 0, 'unrecognizedCheck': 'blocked'}),
    lambda r: r['review'].update(programmaticChecks={'garmentReferenceGuard': 'conservative_literal_absence', 'issuesFound': 1}),
])
def test_export_adapter_only_accepts_known_server_envelope_fields(tmp_path, change):
    svc, store = service(tmp_path)
    exported = confirmed_export_regression()
    change(exported)
    source = task(store, change=lambda result: result.update(exported))
    with pytest.raises(ServiceError, match='CHARACTER_SCHEMA_INVALID'):
        svc.create_character({'sourceTaskId': source, 'purpose': '拒绝未知字段离线回归'})
    assert svc.list_characters() == []


def test_newer_review_programmatic_metadata_stays_separate_from_cultural_contract(tmp_path):
    svc, store = service(tmp_path)
    exported = confirmed_export_regression()
    exported['review']['programmaticChecks'] = {'garmentReferenceGuard': 'conservative_literal_absence', 'issuesFound': 0}
    source = task(store, change=lambda result: result.update(exported))
    created = svc.create_character({'sourceTaskId': source, 'purpose': '新审校追踪字段离线回归'})
    assert created['reviewSnapshot'] == {key: value for key, value in exported['review'].items()
                                        if key not in ('execution', 'programmaticChecks')}


def test_unknown_task_and_client_supplied_design_cannot_create_asset(tmp_path):
    svc, store = service(tmp_path)
    with pytest.raises(ServiceError, match='AGENT_TASK_NOT_FOUND'):
        svc.create_character({'sourceTaskId': '11111111-1111-1111-1111-111111111111', 'purpose': '测试'})
    with pytest.raises(ValidationError):
        CreateAsset.model_validate({'sourceTaskId': '11111111-1111-1111-1111-111111111111', 'purpose': '测试', 'design': fixture_result()['design'], 'userConfirmed': True})


def test_evidence_mismatch_and_extra_character_fields_rejected(tmp_path):
    svc, store = service(tmp_path)
    for change in [lambda r: r['design']['usedEvidenceIds'].append('unrelated'),
                   lambda r: r['design'].update(modelUrl='https://evil.invalid/model.glb'),
                   lambda r: r['citations'].append(copy.deepcopy(r['citations'][0]))]:
        task_id = task(store, change=change)
        with pytest.raises(ServiceError, match='ASSET_EVIDENCE_INVALID|CHARACTER_SCHEMA_INVALID'):
            svc.create_character({'sourceTaskId': task_id, 'purpose': '测试'})


def test_prompt_is_deterministic_but_changes_with_design():
    design = fixture_result()['design']
    first = visual_prompt(design)
    assert first == visual_prompt(copy.deepcopy(design)) and not first['approved']
    assert '原创设计' in first['imagePrompt'] and '文化依据' in first['imagePrompt']
    assert '靠旗' in first['limitations'][-1]
    design['name'] = '不同离线角色'
    assert visual_prompt(design)['promptHash'] != first['promptHash']


def test_enterprise_brief_is_separate_and_required(tmp_path):
    svc, store = service(tmp_path)
    with pytest.raises(ValidationError):
        CreateAsset.model_validate({'sourceTaskId': '11111111-1111-1111-1111-111111111111', 'mode': 'enterprise', 'purpose': '测试'})
    brief = {'organizationType': 'tourism', 'audience': '访客', 'useCase': '文旅展示', 'designGoal': '文化体验',
             'culturalBoundaries': '不编造史实', 'deliveryScope': '仅模型展示', 'licenseStatus': 'unverified'}
    created = asset(svc, store, mode='enterprise', enterpriseBrief=brief)
    assert created['enterpriseBrief'] == brief and 'enterpriseBrief' not in created['characterSnapshot']


def test_visual_and_image_confirmation_hash_gate_persists(tmp_path):
    svc, store = service(tmp_path)
    created = asset(svc, store)
    with pytest.raises(ServiceError, match='VISUAL_APPROVAL_REQUIRED'):
        svc.upload_image(created['assetId'], image_bytes(), 'image/png', 'manual_image', '离线原创图片')
    with pytest.raises(ServiceError, match='ASSET_STALE_PROMPT'):
        svc.approve_visual(created['assetId'], '0' * 64)
    confirmed = svc.approve_visual(created['assetId'], created['visualPrompt']['promptHash'])
    image = svc.upload_image(created['assetId'], image_bytes(), 'image/png', 'manual_image', '离线原创图片')
    assert not image['accepted'] and 'storageKey' not in image
    with pytest.raises(ServiceError, match='ASSET_STALE_IMAGE'):
        svc.accept_image(image['imageId'], '0' * 64)
    accepted = svc.accept_image(image['imageId'], image['hash'])
    assert accepted['accepted']
    assert AssetService(svc.settings, store).get_image(image['imageId'])['accepted']
    assert confirmed['visualPrompt']['approvedAt'] is not None


@pytest.mark.parametrize('fmt,mime', [('PNG', 'image/png'), ('JPEG', 'image/jpeg'), ('WEBP', 'image/webp')])
def test_real_image_decoding_and_normalization(fmt, mime):
    normalized, meta = normalize_image(image_bytes(fmt=fmt), mime)
    assert normalized.startswith(b'\x89PNG') and meta['mimeType'] == 'image/png'
    assert meta['width'] == 32 and meta['height'] == 48
    assert len(meta['hash']) == 64 and meta['normalization']


@pytest.mark.parametrize('raw,mime', [(b'not image', 'image/png'), (image_bytes(), 'image/jpeg'), (b'<svg></svg>', 'image/svg+xml'),
                                    (image_bytes(size=(2, 2)), 'image/png'), (b'', 'image/png')])
def test_invalid_or_misdeclared_images_rejected(raw, mime):
    with pytest.raises(ServiceError):
        normalize_image(raw, mime)


def test_oversized_image_is_rejected_before_decode():
    with pytest.raises(ServiceError, match='IMAGE_TOO_LARGE'):
        normalize_image(b'x' * (MAX_IMAGE_BYTES + 1), 'image/png')


def test_real_geometry_structural_validation():
    result = validate_glb(glb())
    assert result['valid'] and result['selfContained'] and result['meshCount'] == 1
    assert result['vertexCount'] == 4 and result['triangleCount'] == 4
    assert result['fullConformanceChecked'] is False


@pytest.mark.parametrize('fmt,mime', [('PNG', 'image/png'), ('JPEG', 'image/jpeg')])
def test_glb_embedded_textures_are_actually_decoded_and_bounded(fmt, mime):
    raw = textured_glb(fmt=fmt, mime=mime)
    checked = validate_glb(raw)
    assert checked['imageCount'] == checked['textureCount'] == checked['materialCount'] == 1
    assert checked['decodedTexturePixels'] == 32 * 48 and checked['embeddedImagesDecoded']
    assert checked['fullConformanceChecked'] is False


@pytest.mark.parametrize('raw,mime', [(b'not an image', 'image/png'), (image_bytes(), 'image/jpeg'),
                                    (image_bytes(fmt='GIF'), 'image/png'), (b'<svg></svg>', 'image/svg+xml'),
                                    (image_bytes()[:40], 'image/png')])
def test_glb_malformed_mismatched_or_unsupported_images_are_rejected(raw, mime):
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_INVALID'):
        validate_glb(textured_glb([raw], mime=mime))


@pytest.mark.parametrize('mutation', [
    lambda d: d['images'][0].update(bufferView=9999),
    lambda d: d['bufferViews'][2].update(byteStride=4),
    lambda d: d['textures'][0].update(source=9999),
    lambda d: d['textures'][0].update(sampler=9999),
    lambda d: d['samplers'][0].update(magFilter=True),
    lambda d: d['materials'][0]['pbrMetallicRoughness']['baseColorTexture'].update(index=9999),
    lambda d: d['materials'][0]['pbrMetallicRoughness']['baseColorTexture'].update(texCoord=-1),
    lambda d: d['meshes'][0]['primitives'][0].update(material=9999),
    lambda d: d['materials'][0].update(extensions={'KHR_materials_clearcoat': {'clearcoatTexture': {'index': 9999}}}),
])
def test_glb_texture_material_and_sampler_references_are_checked(mutation):
    original = textured_glb()
    doc = parse_glb(original)
    mutation(doc)
    json_size = struct.unpack_from('<I', original, 12)[0]
    binary = original[20 + json_size + 8:]
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_INVALID'):
        validate_glb(glb(doc, binary))


def test_glb_texture_default_dimension_budget_rejects_before_browser_load():
    # A real, small compressed raster can still exceed the allowed width.
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_TOO_LARGE'):
        validate_glb(textured_glb([image_bytes(size=(8193, 1))]))


def test_glb_texture_pixel_and_total_budgets_apply_before_expensive_decode(monkeypatch):
    # Use small limits to exercise the actual decode-budget branches cheaply;
    # production defaults remain 16M per image and 32M across all images.
    monkeypatch.setattr('backend.app.assets.validation.MAX_TEXTURE_PIXELS', 20)
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_TOO_LARGE'):
        validate_glb(textured_glb([image_bytes(size=(5, 5))]))
    monkeypatch.setattr('backend.app.assets.validation.MAX_TEXTURE_PIXELS', 16_000_000)
    monkeypatch.setattr('backend.app.assets.validation.MAX_TOTAL_TEXTURE_PIXELS', 32)
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_TOO_LARGE'):
        validate_glb(textured_glb([image_bytes(size=(4, 4))] * 3))


def test_glb_too_many_embedded_images_are_rejected():
    with pytest.raises(ServiceError, match='MODEL_TEXTURE_TOO_LARGE'):
        validate_glb(textured_glb([image_bytes(size=(1, 1))] * 17))


@pytest.mark.parametrize('mutation', [
    lambda d: d['buffers'][0].update(uri='https://evil.invalid/geometry.bin'),
    lambda d: d.update(images=[{'uri': 'data:image/png;base64,test'}]),
    lambda d: d['bufferViews'][0].update(byteLength=100000),
    lambda d: d['accessors'][0].update(count=999999),
    lambda d: d['accessors'][0].update(componentType={}),
    lambda d: d['nodes'][0].update(children=[0]),
    lambda d: d['scenes'][0].update(nodes=[]),
    lambda d: d['meshes'][0]['primitives'][0].update(mode=0),
    lambda d: d.update(extensionsRequired=['KHR_draco_mesh_compression']),
])
def test_invalid_glb_structure_or_external_resource_is_rejected(mutation):
    doc = parse_glb(glb())
    mutation(doc)
    with pytest.raises(ServiceError):
        validate_glb(glb(doc))


@pytest.mark.parametrize('raw', [b'not glb', glb()[:-4], b'<html>error</html>', b'glTF' + b'\0' * 16])
def test_corrupt_glb_files_rejected(raw):
    with pytest.raises(ServiceError, match='MODEL_INVALID'):
        validate_glb(raw)


def test_nonfinite_degenerate_and_invalid_indices_rejected():
    valid = glb()
    json_size = struct.unpack_from('<I', valid, 12)[0]
    binary_offset = 20 + json_size + 8
    for offset, value, fmt in [(binary_offset, float('nan'), '<f'), (binary_offset + 48, 65535, '<H')]:
        corrupt = bytearray(valid)
        struct.pack_into(fmt, corrupt, offset, value)
        with pytest.raises(ServiceError):
            validate_glb(bytes(corrupt))
    corrupt = bytearray(valid)
    corrupt[binary_offset:binary_offset + 48] = bytes(48)
    with pytest.raises(ServiceError):
        validate_glb(bytes(corrupt))


def test_import_has_cultural_hash_links_and_never_claims_neural_generation(tmp_path):
    svc, store = service(tmp_path)
    created = asset(svc, store)
    model = svc.import_model(created['assetId'], glb(), '离线原创几何，允许测试')
    assert model['origin'] == 'licensed_import' and model['sourceResultHash'] == created['sourceResultHash']
    assert model['citationHash'] == created['citationHash'] and 'storageKey' not in model
    assert svc.file_path('model', model['modelId']).read_bytes() == glb()
    assert svc.list_models()[0]['modelId'] == model['modelId']
    assert svc.get_character(created['assetId'])['models'][0]['modelId'] == model['modelId']


def test_fixture_is_explicitly_separate_and_repeated_registration_is_safe(tmp_path):
    svc, store = service(tmp_path)
    fixture = svc.register_fixture(glb(), '本测试自产几何，供离线测试使用')
    duplicate = svc.register_fixture(glb(), '本测试自产几何，供离线测试使用')
    assert fixture['modelId'] == duplicate['modelId'] and fixture['assetId'] is None
    assert fixture['origin'] == 'local_test_fixture' and fixture['sourceResultHash'] is None
    assert svc.list_characters() == [] and len(svc.list_models()) == 1


def test_file_tamper_and_storage_traversal_rejected(tmp_path):
    svc, store = service(tmp_path)
    fixture = svc.register_fixture(glb(), '本测试自产几何')
    path = svc.file_path('model', fixture['modelId'])
    corrupt = bytearray(path.read_bytes())
    corrupt[-1] ^= 1
    path.write_bytes(corrupt)
    with pytest.raises(ServiceError, match='ASSET_FILE_CHANGED'):
        svc.file_path('model', fixture['modelId'])
    with svc.store.connect() as db:
        item = svc.store.file('model', fixture['modelId'])
        item['storageKey'] = '../../private.env'
        db.execute('UPDATE asset_models SET content_json=? WHERE model_id=?', (json.dumps(item), fixture['modelId']))
    with pytest.raises(ServiceError, match='ASSET_STORAGE_INVALID'):
        svc.file_path('model', fixture['modelId'])


def test_json_and_binary_http_routes_are_safe_and_range_capable(tmp_path):
    svc, store = service(tmp_path)
    created = asset(svc, store)
    client = api(svc)
    approved = client.post(f"/api/v1/assets/characters/{created['assetId']}/visual-approval", json={'promptHash': created['visualPrompt']['promptHash'], 'action': 'accept'})
    assert approved.status_code == 200
    upload = client.post('/api/v1/assets/images', params={'assetId': created['assetId'], 'provenance': 'manual_image', 'licenseNote': '本测试自产图片'},
                         content=image_bytes(), headers={'Content-Type': 'image/png'})
    assert upload.status_code == 201
    image = upload.json()
    assert client.post(f"/api/v1/assets/images/{image['imageId']}/accept", json={'imageHash': image['hash'], 'action': 'accept'}).status_code == 200
    assert client.get(image['fileUrl']).headers['content-type'] == 'image/png'
    imported = client.post('/api/v1/assets/models/import', params={'assetId': created['assetId'], 'licenseNote': '本测试自产几何'},
                           content=glb(), headers={'Content-Type': 'model/gltf-binary'})
    assert imported.status_code == 201
    model = imported.json()
    full = client.get(model['fileUrl'])
    assert full.status_code == 200 and full.content == glb()
    assert full.headers['content-type'] == 'model/gltf-binary'
    ranged = client.get(model['fileUrl'], headers={'Range': 'bytes=0-11'})
    assert ranged.status_code == 206 and ranged.content == glb()[:12]
    assert client.get(model['downloadUrl']).headers['content-disposition'].startswith('attachment;')
    assert 'storageKey' not in imported.text and str(tmp_path) not in imported.text
    assert client.get('/api/v1/assets/models/missing/file').status_code == 404


def test_api_upload_limits_and_fake_creation_denied(tmp_path):
    svc, store = service(tmp_path)
    created = asset(svc, store)
    client = api(svc)
    params = {'assetId': created['assetId'], 'provenance': 'manual_image', 'licenseNote': '本测试自产图片'}
    oversized = client.post('/api/v1/assets/images', params=params, content=b'x', headers={'Content-Type': 'image/png', 'Content-Length': str(MAX_IMAGE_BYTES + 1)})
    assert oversized.status_code == 413
    assert client.post('/api/v1/assets/images', params=params, content=b'', headers={'Content-Type': 'image/png'}).status_code == 422
    assert client.post('/api/v1/assets/characters', json={'sourceTaskId': created['sourceTaskId'], 'purpose': '测试', 'userConfirmed': True}).status_code == 422
    assert client.post('/api/v1/assets/model-tasks', json={'approvalId': '11111111-1111-1111-1111-111111111111', 'modelCount': 1}, headers={'X-Idempotency-Key': 'offline-key'}).status_code == 403
    assert client.get('/api/v1/assets/usage').json()['realEnabled'] is False
    assert client.get('/api/v1/assets/usage').json()['used_calls'] is None


def test_model_count_fixed_to_one_and_no_client_schema_override():
    common = {'assetId': '11111111-1111-1111-1111-111111111111', 'assetVersion': 1,
              'imageId': '11111111-1111-1111-1111-111111111111', 'imageHash': 'a' * 64,
              'promptHash': 'b' * 64, 'purpose': '测试', 'modelCount': 1, 'estimatedCredits': 80, 'action': 'accept'}
    assert ModelApprovalRequest.model_validate(common).modelCount == 1
    for mutation in [{'modelCount': 2}, {'modelCount': True}, {'modelCount': 1.0}, {'apiKey': 'forbidden'}, {'assetVersion': True}]:
        with pytest.raises(ValidationError):
            ModelApprovalRequest.model_validate({**common, **mutation})


def test_internal_generated_registration_requires_accepted_image_and_is_idempotent(tmp_path):
    """Offline completion-hook test; it makes no provider request."""
    svc, store = service(tmp_path)
    created = asset(svc, store)
    svc.approve_visual(created['assetId'], created['visualPrompt']['promptHash'])
    image = svc.upload_image(created['assetId'], image_bytes(), 'image/png', 'imported_ai_image', '离线原创图片，非真实AI生成')
    with pytest.raises(ServiceError, match='ASSET_GENERATION_INPUT_INVALID'):
        svc.register_generated_model(created['assetId'], image['imageId'], glb(), 'offline-provider-task', '离线测试')
    svc.accept_image(image['imageId'], image['hash'])
    model = svc.register_generated_model(created['assetId'], image['imageId'], glb(), 'offline-provider-task', '离线测试')
    same = svc.register_generated_model(created['assetId'], image['imageId'], glb(), 'offline-provider-task', '离线测试')
    assert model['modelId'] == same['modelId'] and model['imageHash'] == image['hash']
    assert model['providerTaskId'] == 'offline-provider-task'
    doc = parse_glb(glb())
    doc['asset']['generator'] = 'changed offline result'
    with pytest.raises(ServiceError, match='MODEL_RESULT_CONFLICT'):
        svc.register_generated_model(created['assetId'], image['imageId'], glb(doc), 'offline-provider-task', '离线测试')


def test_real_licensed_duck_glb_fixture_registration_and_http_file(tmp_path):
    from pathlib import Path
    raw = (Path(__file__).parent / 'fixtures' / 'phase4' / 'Duck.glb').read_bytes()
    checked = validate_glb(raw)
    assert checked['vertexCount'] == 2399 and checked['triangleCount'] == 4212
    assert checked['hash'] == '65bf938f54d6073e619e76e007820bbf980cdc3dc0daec0d94830ffc4ae54ab5'
    assert checked['imageCount'] == 1 and checked['textureCount'] == 1
    assert checked['decodedTexturePixels'] > 0 and checked['embeddedImagesDecoded']
    assert checked['fullConformanceChecked'] is False
    svc, store = service(tmp_path)
    model = svc.register_fixture(raw, 'Khronos glTF Sample Assets Duck ©2006 Sony, SCEA Shared Source License 1.0；仅合法已有GLB验收，不是Neural4D模型或京剧角色。', 'Duck：合法已有GLB查看器测试模型')
    with api(svc) as client:
        assert client.get('/api/v1/assets/models').json()['models'][0]['origin'] == 'local_test_fixture'
        response = client.get(model['fileUrl'])
        assert response.status_code == 200 and response.content == raw
        assert response.headers['content-type'] == 'model/gltf-binary'
        assert client.get(model['fileUrl'], headers={'Range': 'bytes=0-11'}).content == raw[:12]


def test_source_snapshot_change_invalidates_asset_confirmation(tmp_path):
    svc, store = service(tmp_path)
    created = asset(svc, store)
    assert svc.verify_character_snapshot(created['assetId'])['sourceResultHash'] == created['sourceResultHash']
    # Deliberately simulate an out-of-band database migration, not a user API.
    with store.connect() as db:
        changed = store.result(created['sourceTaskId'])
        changed['knowledgeGeneration'] = 'different-offline-generation'
        db.execute('UPDATE agent_tasks SET result_json=? WHERE task_id=?', (json.dumps(changed, ensure_ascii=False), created['sourceTaskId']))
    with pytest.raises(ServiceError, match='ASSET_SOURCE_CHANGED'):
        svc.verify_character_snapshot(created['assetId'])


def test_generated_model_registration_atomic_under_concurrent_retrievals(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    svc, store = service(tmp_path)
    created = asset(svc, store)
    svc.approve_visual(created['assetId'], created['visualPrompt']['promptHash'])
    image = svc.upload_image(created['assetId'], image_bytes(), 'image/png', 'manual_image', '离线自产图片')
    svc.accept_image(image['imageId'], image['hash'])
    with ThreadPoolExecutor(max_workers=4) as workers:
        jobs = [workers.submit(svc.register_generated_model, created['assetId'], image['imageId'], glb(), 'concurrent-offline-task', '离线测试') for _ in range(4)]
        ids = [job.result()['modelId'] for job in jobs]
    assert len(set(ids)) == 1 and len(svc.list_models(created['assetId'])) == 1


def test_same_hash_file_reused_while_open_and_tamper_is_not_silently_repaired(tmp_path):
    svc, store = service(tmp_path)
    raw, digest = glb(), hashlib.sha256(glb()).hexdigest()
    key = svc.save_bytes('models', raw, digest, 'glb')
    path = svc.root / key
    original_identity = path.stat().st_ino
    with path.open('rb') as reader:
        assert svc.save_bytes('models', raw, digest, 'glb') == key
        assert reader.read() == raw and path.stat().st_ino == original_identity
    corrupt = bytearray(raw)
    corrupt[-1] ^= 1
    path.write_bytes(corrupt)
    with pytest.raises(ServiceError, match='ASSET_FILE_CHANGED'):
        svc.save_bytes('models', raw, digest, 'glb')
    assert path.read_bytes() == bytes(corrupt)
    assert list(path.parent.glob('*.part')) == []


def test_concurrent_hash_publish_is_atomic_no_overwrite_and_cleans_temporary_files(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    svc, store = service(tmp_path)
    raw, digest, barrier = glb(), hashlib.sha256(glb()).hexdigest(), Barrier(8)
    def save():
        barrier.wait(timeout=5)
        return svc.save_bytes('models', raw, digest, 'glb')
    with ThreadPoolExecutor(max_workers=8) as workers:
        keys = list(workers.map(lambda _: save(), range(8)))
    assert len(set(keys)) == 1 and (svc.root / keys[0]).read_bytes() == raw
    assert list((svc.root / 'models').glob('*.part')) == []
    assert len(list((svc.root / 'models').glob('*.glb'))) == 1
