"""OFFLINE synthetic internal-input tests; no real Neural4D or quota writes."""
import copy
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.assets.candidates import CandidateCatalog
from backend.app.assets.technical_test import (freeze_technical_candidate,
                                             technical_image_path,
                                             register_technical_model)
from backend.app.assets.visual_prompt import canonical_hash
from backend.app.errors import ServiceError
from backend.tests.test_phase4_assets import service, image_bytes, glb, parse_glb


def candidate(catalog, scope='offline-first-chibi-test', *, style='chibi', text='仅离线候选Prompt', raw=None):
    return catalog.register(raw or image_bytes(), 'image/png', scope,
                            '离线未知来源，不是真实资料', '离线许可声明，未经核实',
                            {'version': 'offline-chibi-v2', 'text': text}, styleMode=style)


@pytest.fixture
def prepared(tmp_path):
    assets, _ = service(tmp_path)
    catalog = CandidateCatalog(assets)
    old = catalog.import_history({'sha256': '1' * 64, 'styleMode': 'chibi',
                                  'source': '旧离线来源', 'licenseStatement': '旧离线声明'},
                                 'offline-first-chibi-test')
    current = candidate(catalog)
    assert old['version'] == 1 and current['version'] == 2
    data = {'candidateId': current['candidateId'], 'sourceImageHash': current['sourceHash'],
            'imageHash': current['hash'], 'promptHash': current['promptSnapshot']['promptHash'],
            'styleMode': 'chibi', 'purpose': '技术验证', 'modelCount': 1,
            'authorizationEvidenceHash': 'a' * 64, 'permissionEvidenceHash': 'b' * 64}
    return assets, catalog, current, data


def test_freeze_is_internal_does_not_confirm_candidate_or_formal_character(prepared):
    assets, catalog, current, data = prepared
    payload = freeze_technical_candidate(assets, data)
    assert payload['assetKind'] == 'internal_technical_test'
    assert payload['candidateId'] == current['candidateId']
    assert payload['candidateVersion'] == payload['styleVersion'] == 2
    assert payload['purpose'] == '技术验证' and payload['modelCount'] == 1
    assert payload['parameters']['modelCount'] == '1'
    assert payload['parameters']['faceNum'] == '100000'
    for field in ('characterId', 'assetId', 'sourceTaskId', 'sourceResultHash',
                  'citationHash', 'imageId', 'assetVersion'):
        assert payload[field] is None
    assert payload['internalUseOnly'] is True and payload['visibility'] == 'internal'
    for field in ('cultureAlignmentVerified', 'publicationAllowed', 'licenseVerified', 'commercialUseVerified'):
        assert payload[field] is False
    assert catalog.get(current['candidateId']) == current
    assert current['accepted'] is current['modelEligible'] is False
    assert assets.usage is None and assets.model_service is None
    with assets.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM character_assets').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM asset_images').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM asset_models').fetchone()[0] == 0


def test_frozen_payload_roundtrip_and_actual_png_hash(prepared):
    assets, catalog, current, data = prepared
    payload = freeze_technical_candidate(assets, data)
    assert freeze_technical_candidate(assets, payload) == payload
    path = technical_image_path(assets, payload)
    assert path == catalog.file_path(current['candidateId'])
    assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == payload['imageHash']


@pytest.mark.parametrize('change', [
    {'modelCount': 2}, {'modelCount': True}, {'styleMode': 'realistic'}, {'purpose': '正式角色建模'},
    {'characterId': 'forged-role'}, {'assetId': 'forged-asset'}, {'sourceTaskId': 'forged-task'},
    {'sourceResultHash': 'c' * 64}, {'citationHash': 'c' * 64}, {'imageId': 'forged-image'},
    {'assetVersion': 2}, {'publicationAllowed': True}, {'cultureAlignmentVerified': True},
    {'licenseVerified': True}, {'commercialUseVerified': True}, {'assetKind': 'character_asset'},
    {'internalUseOnly': False}, {'visibility': 'public'},
])
def test_technical_envelope_cannot_grant_formal_identity_or_permissions(prepared, change):
    assets, _, _, data = prepared
    with pytest.raises(ServiceError):
        freeze_technical_candidate(assets, {**data, **change})


@pytest.mark.parametrize('field', ['sourceImageHash', 'imageHash', 'promptHash',
                                   'authorizationEvidenceHash', 'permissionEvidenceHash'])
@pytest.mark.parametrize('invalid', ['', None, 'not-a-hash', 'A' * 64])
def test_public_evidence_and_input_hashes_required(prepared, field, invalid):
    assets, _, _, data = prepared
    with pytest.raises(ServiceError) as error:
        freeze_technical_candidate(assets, {**data, field: invalid})
    assert error.value.code == 'NEURAL4D_TECHNICAL_INPUT_INVALID'


@pytest.mark.parametrize('field', ['sourceImageHash', 'imageHash', 'promptHash'])
def test_valid_format_changed_input_hash_rejected(prepared, field):
    assets, _, _, data = prepared
    with pytest.raises(ServiceError) as error:
        freeze_technical_candidate(assets, {**data, field: 'e' * 64})
    assert error.value.code == 'NEURAL4D_INPUT_CHANGED'


def test_legacy_missing_image_and_v1_live_candidate_rejected(prepared):
    assets, catalog, _, data = prepared
    legacy = next(item for item in catalog.list() if item['version'] == 1)
    for item in (legacy, candidate(catalog, scope='offline-other-first-version')):
        with pytest.raises(ServiceError) as error:
            freeze_technical_candidate(assets, {**data, 'candidateId': item['candidateId']})
        assert error.value.code == 'NEURAL4D_TECHNICAL_CANDIDATE_INVALID'


def test_style_does_not_change_culture_checks_or_forge_new_role(prepared):
    assets, catalog, _, data = prepared
    catalog.import_history({'sha256': '2' * 64, 'styleMode': 'chibi'}, 'offline-other-scope')
    another = candidate(catalog, scope='offline-other-scope')
    payload = freeze_technical_candidate(assets, {**data, 'candidateId': another['candidateId']})
    assert payload['characterId'] is None and payload['sourceTaskId'] is None
    assert payload['cultureAlignmentVerified'] is False
    assert payload['publicationAllowed'] is False
    assert payload['candidateScope'] == 'offline-other-scope'


def test_realistic_candidate_cannot_use_chibi_technical_path(prepared):
    assets, catalog, _, data = prepared
    newer = candidate(catalog, style='realistic')
    with pytest.raises(ServiceError) as error:
        freeze_technical_candidate(assets, {**data, 'candidateId': newer['candidateId']})
    assert error.value.code == 'NEURAL4D_TECHNICAL_CANDIDATE_INVALID'


def test_new_scope_version_invalidates_unsent_payload(prepared):
    assets, catalog, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    candidate(catalog, text='新的离线Prompt版本')
    for fn, argument in ((freeze_technical_candidate, data), (technical_image_path, payload)):
        with pytest.raises(ServiceError) as error:
            fn(assets, argument)
        assert error.value.code == 'NEURAL4D_APPROVAL_STALE'


def test_new_other_scope_does_not_invalidate_existing_branch(prepared):
    assets, catalog, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    candidate(catalog, scope='offline-independent-scope')
    assert technical_image_path(assets, payload).exists()


def test_self_hash_prompt_tampering_rejected_without_database_changes(prepared, monkeypatch):
    assets, catalog, current, data = prepared
    tampered = copy.deepcopy(current)
    tampered['promptSnapshot']['text'] = '伪造修改，不更新Hash'
    monkeypatch.setattr(CandidateCatalog, 'get', lambda self, candidate_id: tampered)
    with pytest.raises(ServiceError) as error:
        freeze_technical_candidate(assets, data)
    assert error.value.code == 'NEURAL4D_TECHNICAL_PROMPT_INVALID'


@pytest.mark.parametrize('extra', [{'unrecognizedGrant': True}, {'promptVersion': 'forged'},
                                  {'candidateVersion': 99}, {'styleVersion': 99},
                                  {'candidateScope': 'forged'}, {'parameters': {'modelCount': '2'}}])
def test_frozen_payload_cannot_be_modified_or_extended(prepared, extra):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    with pytest.raises(ServiceError):
        technical_image_path(assets, {**payload, **extra})


@pytest.mark.parametrize('kind', ['preview', 'original'])
def test_file_changed_after_freeze_rejected(prepared, kind):
    assets, catalog, current, data = prepared
    payload = freeze_technical_candidate(assets, data)
    path = catalog.file_path(current['candidateId'], kind)
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ServiceError) as error:
        technical_image_path(assets, payload)
    assert error.value.code == 'CANDIDATE_FILE_CHANGED'


def test_generated_technical_model_has_true_null_role_and_local_lineage(prepared):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    model = register_technical_model(assets, payload, glb(), 'offline-provider-task-1')
    stored = assets.store.file('model', model['modelId'])
    assert stored['assetId'] is stored['characterId'] is stored['sourceTaskId'] is None
    assert stored['sourceResultHash'] is stored['citationHash'] is None
    assert stored['origin'] == 'neural4d_technical_test'
    assert stored['styleMode'] == 'chibi' and stored['styleVersion'] == 2
    assert stored['candidateId'] == payload['candidateId']
    assert stored['imageHash'] == payload['imageHash']
    assert stored['sourceImageHash'] == payload['sourceImageHash']
    assert stored['promptHash'] == payload['promptHash']
    assert stored['frozenPayloadHash'] == canonical_hash(payload)
    assert stored['internalUseOnly'] is True and stored['visibility'] == 'internal'
    assert stored['publicationAllowed'] is stored['cultureAlignmentVerified'] is False
    assert assets.file_path('model', model['modelId']).read_bytes() == glb()
    assert assets.usage is None and assets.model_service is None


def test_completed_task_duplicate_is_idempotent_and_keeps_historical_snapshot(prepared):
    assets, catalog, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    first = register_technical_model(assets, payload, glb(), 'offline-provider-task-2')
    candidate(catalog, text='新待审版本不会破坏已请求任务')
    assert register_technical_model(assets, payload, glb(), 'offline-provider-task-2') == first
    with assets.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM asset_models').fetchone()[0] == 1


def test_same_provider_task_cannot_be_rebound_to_different_frozen_input(prepared):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    register_technical_model(assets, payload, glb(), 'offline-provider-task-3')
    changed = {**payload, 'authorizationEvidenceHash': 'c' * 64}
    with pytest.raises(ServiceError) as error:
        register_technical_model(assets, changed, glb(), 'offline-provider-task-3')
    assert error.value.code == 'MODEL_RESULT_CONFLICT'


def test_bad_or_different_glb_output_rejected(prepared):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    with pytest.raises(ServiceError):
        register_technical_model(assets, payload, b'not GLB', 'offline-provider-task-4')
    register_technical_model(assets, payload, glb(), 'offline-provider-task-4')
    doc = parse_glb(glb())
    doc['asset']['generator'] = 'distinct offline original geometry metadata'
    with pytest.raises(ServiceError) as error:
        register_technical_model(assets, payload, glb(doc), 'offline-provider-task-4')
    assert error.value.code == 'MODEL_RESULT_CONFLICT'


def test_concurrent_completion_keeps_one_model_and_same_input(prepared):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    with ThreadPoolExecutor(max_workers=8) as pool:
        models = list(pool.map(lambda _: register_technical_model(
            assets, payload, glb(), 'offline-provider-task-parallel'), range(8)))
    assert len({model['modelId'] for model in models}) == 1
    with assets.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM asset_models').fetchone()[0] == 1


@pytest.mark.parametrize('provider_task_id', ['', None, 'bad\nidentifier', 'x' * 201])
def test_invalid_supplier_identifier_not_saved(prepared, provider_task_id):
    assets, _, _, data = prepared
    payload = freeze_technical_candidate(assets, data)
    with pytest.raises(ServiceError) as error:
        register_technical_model(assets, payload, glb(), provider_task_id)
    assert error.value.code == 'NEURAL4D_RESPONSE_INVALID'
    with assets.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM asset_models').fetchone()[0] == 0
