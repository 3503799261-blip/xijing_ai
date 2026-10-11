"""OFFLINE incremental style contracts. No provider, generation or network."""
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from pydantic import ValidationError
from backend.app.assets.schemas import CreateAsset, PromptVersionRequest, ModelApprovalRequest
from backend.app.assets.service import AssetService
from backend.app.assets.visual_prompt import visual_prompt
from backend.app.errors import ServiceError
from backend.tests.test_phase4_assets import service, task, fixture_result, image_bytes, glb, api


def styles(svc, store):
    source_task = task(store)
    common = {'sourceTaskId': source_task, 'mode': 'personal', 'purpose': '离线双风格测试'}
    realistic = svc.create_character(common)
    chibi = svc.create_character({**common, 'styleMode': 'chibi'})
    return realistic, chibi


def edit(asset, text='仅离线Prompt编辑草稿，不是文化审核结果。'):
    return {'expectedPromptHash': asset['visualPrompt']['promptHash'], 'imagePrompt': text,
            'negativePrompt': '仅离线草稿约束', 'action': 'create_version'}


def test_dual_style_same_culture_family_distinct_assets_and_templates(tmp_path):
    svc, store = service(tmp_path)
    realistic, chibi = styles(svc, store)
    assert realistic['styleMode'] == 'realistic' and chibi['styleMode'] == 'chibi'
    assert realistic['characterId'] == chibi['characterId']
    assert realistic['assetId'] != chibi['assetId']
    assert realistic['sourceResultHash'] == chibi['sourceResultHash']
    assert realistic['characterSnapshot'] == chibi['characterSnapshot']
    assert realistic['reviewSnapshot'] == chibi['reviewSnapshot']
    assert realistic['citationSnapshot'] == chibi['citationSnapshot']
    assert realistic['visualPrompt']['promptHash'] != chibi['visualPrompt']['promptHash']
    assert realistic['visualPrompt']['styleTemplateVersion'] != chibi['visualPrompt']['styleTemplateVersion']
    assert not realistic['culturalReviewRequired'] and not chibi['culturalReviewRequired']
    assert '自然人体比例' in realistic['visualPrompt']['imagePrompt']
    assert 'Q版卡通' in chibi['visualPrompt']['imagePrompt']
    assert '不得自动删改靠旗' in chibi['visualPrompt']['imagePrompt']
    assert '不是新增文化事实' in chibi['visualPrompt']['imagePrompt']
    assert len(svc.list_styles(realistic['assetId'])['characters']) == 2
    assert store.result(realistic['sourceTaskId'])['design'] == fixture_result()['design']


def test_style_create_idempotence_and_deterministic_templates(tmp_path):
    svc, store = service(tmp_path)
    realistic, chibi = styles(svc, store)
    common = {'sourceTaskId': realistic['sourceTaskId'], 'purpose': realistic['purpose']}
    assert svc.create_character(common)['assetId'] == realistic['assetId']
    assert svc.create_character({**common, 'styleMode': 'chibi'})['assetId'] == chibi['assetId']
    assert visual_prompt(fixture_result()['design'], 'chibi') == visual_prompt(fixture_result()['design'], 'chibi')
    assert svc.usage is None and svc.model_service is None


@pytest.mark.parametrize('mode', ['cartoon', 'enterprise', '', 1, None, True])
def test_unknown_styles_are_rejected_and_not_created(mode):
    with pytest.raises(ValidationError):
        CreateAsset.model_validate({'sourceTaskId': '11111111-1111-1111-1111-111111111111', 'purpose': '测试', 'styleMode': mode})


def test_two_styles_images_models_are_isolated_and_carry_metadata(tmp_path):
    svc, store = service(tmp_path)
    assets = styles(svc, store)
    for asset in assets:
        svc.approve_visual(asset['assetId'], asset['visualPrompt']['promptHash'])
        image = svc.upload_image(asset['assetId'], image_bytes(), 'image/png', 'manual_image', '离线自产图片')
        svc.accept_image(image['imageId'], image['hash'])
        model = svc.import_model(asset['assetId'], glb(), '离线自产模型')
        assert image['styleMode'] == model['styleMode'] == asset['styleMode']
        assert image['styleVersion'] == model['styleVersion'] == 1
        assert image['characterId'] == model['characterId'] == asset['characterId']
        assert image['promptHash'] == asset['visualPrompt']['promptHash']
    real, chibi = map(lambda a: svc.get_character(a['assetId']), assets)
    assert real['images'][0]['imageId'] != chibi['images'][0]['imageId']
    assert real['models'][0]['modelId'] != chibi['models'][0]['modelId']
    assert real['images'][0]['hash'] == chibi['images'][0]['hash']
    assert real['models'][0]['origin'] == 'licensed_import'


def test_prompt_edits_create_new_locked_version_and_preserve_old_files_approvals(tmp_path):
    svc, store = service(tmp_path)
    old, other = styles(svc, store)
    svc.approve_visual(old['assetId'], old['visualPrompt']['promptHash'])
    image = svc.upload_image(old['assetId'], image_bytes(), 'image/png', 'manual_image', '离线自产图片')
    svc.accept_image(image['imageId'], image['hash'])
    model = svc.import_model(old['assetId'], glb(), '离线自产模型')
    original = svc.get_character(old['assetId'])
    draft = svc.create_prompt_version(old['assetId'], edit(old))
    assert draft['assetId'] != old['assetId'] and draft['parentAssetId'] == old['assetId']
    assert draft['version'] == draft['styleVersion'] == 2
    assert draft['styleMode'] == 'realistic' and draft['characterId'] == old['characterId']
    assert draft['sourceResultHash'] == old['sourceResultHash']
    assert draft['visualPrompt']['promptHash'] != old['visualPrompt']['promptHash']
    assert draft['visualPrompt']['approved'] is False and draft['visualPrompt']['approvedAt'] is None
    assert draft['images'] == draft['models'] == []
    assert draft['culturalReviewRequired'] and draft['visualPrompt']['editableDraft']
    assert svc.get_character(old['assetId']) == original
    assert svc.get_character(other['assetId'])['styleVersion'] == 1
    assert svc.file_path('image', image['imageId']).read_bytes()
    assert svc.file_path('model', model['modelId']).read_bytes() == glb()
    assert svc.create_prompt_version(old['assetId'], edit(old))['assetId'] == draft['assetId']
    reopened = AssetService(svc.settings, store)
    assert reopened.get_character(draft['assetId'])['culturalReviewRequired']


def test_free_edit_culture_gate_cannot_be_cleared_by_visual_confirm_or_client_scope(tmp_path):
    svc, store = service(tmp_path)
    old, _ = styles(svc, store)
    draft = svc.create_prompt_version(old['assetId'], edit(old, '自由编辑可能改变文化表达，必须复核。'))
    with pytest.raises(ServiceError, match='CULTURAL_REVIEW_REQUIRED'):
        svc.approve_visual(draft['assetId'], draft['visualPrompt']['promptHash'])
    with pytest.raises(ServiceError, match='CULTURAL_REVIEW_REQUIRED'):
        svc.store.approve_visual(draft['assetId'], draft['visualPrompt']['promptHash'])
    with pytest.raises(ServiceError, match='CULTURAL_REVIEW_REQUIRED'):
        svc.upload_image(draft['assetId'], image_bytes(), 'image/png', 'manual_image', '离线自产图片')
    with pytest.raises(ValidationError):
        PromptVersionRequest.model_validate({**edit(old), 'scope': 'visual_only', 'culturalReviewRequired': False})


@pytest.mark.parametrize('style_mode', ['realistic', 'chibi'])
def test_pending_culture_draft_import_service_denies_before_parse_or_write(tmp_path, monkeypatch, style_mode):
    svc, store = service(tmp_path)
    old = svc.create_character({'sourceTaskId': task(store), 'purpose': '离线文化门禁测试', 'styleMode': style_mode})
    draft = svc.create_prompt_version(old['assetId'], edit(old))
    original = svc.get_character(old['assetId'])

    def forbidden(*args, **kwargs):
        raise AssertionError('Pending cultural draft reached GLB parsing or file write.')

    monkeypatch.setattr('backend.app.assets.service.validate_glb', forbidden)
    monkeypatch.setattr(svc, 'save_bytes', forbidden)
    with pytest.raises(ServiceError, match='CULTURAL_REVIEW_REQUIRED'):
        svc.import_model(draft['assetId'], glb(), '离线自产几何')
    assert svc.store.files('model') == []
    assert not (svc.root / 'models').exists()
    assert svc.get_character(old['assetId']) == original
    assert svc.get_character(draft['assetId'])['models'] == []


@pytest.mark.parametrize('style_mode', ['realistic', 'chibi'])
def test_pending_culture_draft_direct_http_import_denied_and_no_registered_file(tmp_path, style_mode):
    svc, store = service(tmp_path)
    old = svc.create_character({'sourceTaskId': task(store), 'purpose': '离线HTTP文化门禁', 'styleMode': style_mode})
    draft = svc.create_prompt_version(old['assetId'], edit(old))
    with api(svc) as client:
        result = client.post('/api/v1/assets/models/import',
                             params={'assetId': draft['assetId'], 'licenseNote': '离线自产几何'},
                             content=glb(), headers={'Content-Type': 'model/gltf-binary'})
        assert result.status_code == 409
        assert result.json()['error']['code'] == 'CULTURAL_REVIEW_REQUIRED'
        assert client.get(f"/api/v1/assets/characters/{draft['assetId']}").json()['models'] == []
        assert client.get('/api/v1/assets/models').json()['models'] == []
    assert not (svc.root / 'models').exists()


def test_prompt_edit_stale_hash_unchanged_text_controls_and_limits(tmp_path):
    svc, store = service(tmp_path)
    old, _ = styles(svc, store)
    with pytest.raises(ServiceError, match='ASSET_STALE_PROMPT'):
        svc.create_prompt_version(old['assetId'], {**edit(old), 'expectedPromptHash': '0' * 64})
    with pytest.raises(ServiceError, match='ASSET_PROMPT_UNCHANGED'):
        svc.create_prompt_version(old['assetId'], {**edit(old), 'imagePrompt': old['visualPrompt']['imagePrompt'],
                                                 'negativePrompt': old['visualPrompt']['negativePrompt']})
    for bad in ['', '   ', 'x' * 3001, 'bad\0input']:
        with pytest.raises(ValidationError):
            PromptVersionRequest.model_validate({**edit(old), 'imagePrompt': bad})


def test_concurrent_different_prompt_edits_get_distinct_monotonic_versions(tmp_path):
    svc, store = service(tmp_path)
    old, _ = styles(svc, store)
    with ThreadPoolExecutor(max_workers=4) as workers:
        jobs = [workers.submit(svc.create_prompt_version, old['assetId'], edit(old, f'仅离线草稿版本{i}')) for i in range(4)]
        versions = [job.result() for job in jobs]
    assert sorted(item['version'] for item in versions) == [2, 3, 4, 5]
    assert len({item['assetId'] for item in versions}) == 4
    assert len({item['visualPrompt']['promptHash'] for item in versions}) == 4
    assert all(item['culturalReviewRequired'] for item in versions)


def test_legacy_records_add_defaults_on_read_without_changing_storage(tmp_path):
    svc, store = service(tmp_path)
    old, _ = styles(svc, store)
    svc.approve_visual(old['assetId'], old['visualPrompt']['promptHash'])
    image = svc.upload_image(old['assetId'], image_bytes(), 'image/png', 'manual_image', '离线自产图片')
    model = svc.import_model(old['assetId'], glb(), '离线自产模型')
    # Simulate the actual pre-dualstyle records; do not migrate them in place.
    with svc.store.connect() as db:
        record = svc.store.get(old['assetId'])
        for key in ('styleMode', 'styleVersion', 'characterId', 'culturalReviewRequired', 'parentAssetId'):
            record.pop(key, None)
        for key in ('styleMode', 'styleVersion', 'styleTemplateVersion', 'styleLabel', 'editableDraft'):
            record['visualPrompt'].pop(key, None)
        record['assetSchemaVersion'] = '1.0'
        db.execute('UPDATE character_assets SET content_json=? WHERE asset_id=?', (json.dumps(record, ensure_ascii=False), old['assetId']))
        for table, key, file_id in [('asset_images', 'image_id', image['imageId']), ('asset_models', 'model_id', model['modelId'])]:
            data = json.loads(db.execute(f'SELECT content_json FROM {table} WHERE {key}=?', (file_id,)).fetchone()[0])
            for field in ('styleMode', 'styleVersion', 'characterId'):
                data.pop(field, None)
            db.execute(f'UPDATE {table} SET content_json=? WHERE {key}=?', (json.dumps(data, ensure_ascii=False), file_id))
    before = svc.store.get(old['assetId'])
    result = svc.get_character(old['assetId'])
    assert result['styleMode'] == 'realistic' and result['styleVersion'] == 1
    assert result['characterId'] == old['characterId'] and result['legacyStyleDefaultsApplied']
    assert result['visualPrompt']['approved'] is True
    assert result['images'][0]['styleMode'] == 'realistic' and result['models'][0]['styleMode'] == 'realistic'
    assert svc.store.get(old['assetId']) == before


def test_family_http_filters_and_prompt_versions_return_safe_json(tmp_path):
    svc, store = service(tmp_path)
    old, chibi = styles(svc, store)
    with api(svc) as client:
        by_family = client.get('/api/v1/assets/characters', params={'characterId': old['characterId'], 'mode': 'personal'})
        assert by_family.status_code == 200 and len(by_family.json()['characters']) == 2
        by_task = client.get('/api/v1/assets/characters', params={'sourceTaskId': old['sourceTaskId']})
        assert len(by_task.json()['characters']) == 2
        assert client.get(f"/api/v1/assets/characters/{old['assetId']}/styles").json()['characterId'] == old['characterId']
        response = client.post(f"/api/v1/assets/characters/{chibi['assetId']}/prompt-versions", json=edit(chibi))
        assert response.status_code == 201 and response.json()['styleMode'] == 'chibi'
        assert response.json()['culturalReviewRequired']
        assert str(tmp_path) not in response.text and 'storageKey' not in response.text
        assert client.get('/api/v1/assets/characters', params={'characterId': 'unrelated'}).json()['characters'] == []


def test_optional_approval_style_fields_validate_without_exposing_vendor_params():
    request = {'assetId': '11111111-1111-1111-1111-111111111111', 'assetVersion': 1,
               'imageId': '22222222-2222-2222-2222-222222222222', 'imageHash': 'a' * 64,
               'promptHash': 'b' * 64, 'purpose': '仅离线测试', 'modelCount': 1, 'estimatedCredits': 80,
               'action': 'accept', 'styleMode': 'chibi', 'styleVersion': 1,
               'characterId': '33333333-3333-3333-3333-333333333333'}
    assert ModelApprovalRequest.model_validate(request).styleMode == 'chibi'
    with pytest.raises(ValidationError):
        ModelApprovalRequest.model_validate({**request, 'styleVersion': True})
    with pytest.raises(ValidationError):
        ModelApprovalRequest.model_validate({**request, 'faceNum': 500000})
