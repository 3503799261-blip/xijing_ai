"""OFFLINE candidate snapshots; synthetic raster bytes, no provider requests."""
import io
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from PIL import Image

from backend.app.assets.candidates import CandidateCatalog
from backend.app.assets.service import AssetService
from backend.app.errors import ServiceError


def image_bytes(color='#f8fcff', fmt='PNG'):
    stream = io.BytesIO()
    Image.new('RGB', (40, 64), color).save(stream, format=fmt)
    return stream.getvalue()


@pytest.fixture
def catalog(tmp_path):
    # No TaskStore is constructed or confirmed; candidates have no character.
    assets = AssetService(SimpleNamespace(rag_data_dir=tmp_path / 'private'), None)
    return CandidateCatalog(assets)


def register(catalog, raw=None, **extras):
    data = {'raw': image_bytes() if raw is None else raw, 'mime': 'image/png',
            'scope': 'first-chibi-technical-validation',
            'sourceNote': '仅离线测试来源声明，未独立核实',
            'licenseNote': '仅离线测试；并非正式许可证明',
            'promptSnapshot': {'version': 'candidate_chibi_v1', 'text': '仅离线候选Prompt，不是文化依据。'},
            'sourcePathLabel': 'D:\\not-read\\concept.png'}
    return catalog.register(**{**data, **extras})


def history():
    return {'recordedAt': '2026-10-11T00:00:00Z', 'path': 'D:\\not-read\\concept.png',
            'styleMode': 'chibi', 'sha256': '1' * 64, 'size': 10, 'width': 600, 'height': 750,
            'source': '仅离线旧候选来源', 'licenseStatus': 'user_declared_non_commercial_use_and_edit',
            'licenseStatement': '仅离线许可声明', 'imageAccepted': False}


def test_current_candidate_frozen_not_approved_or_associated(catalog):
    item = register(catalog)
    assert item['version'] == 1
    assert item['styleMode'] == 'chibi'
    assert item['characterId'] is item['assetId'] is item['sourceTaskId'] is None
    for field in ('accepted', 'imageAccepted', 'modelEligible', 'modelCreated',
                  'cultureAlignmentVerified', 'sourceVerified', 'licenseVerified',
                  'commercialUseVerified', 'publicRedistributionVerified'):
        assert item[field] is False
    prompt = item['promptSnapshot']
    assert prompt['frozenForReview'] is True and prompt['approved'] is False
    assert prompt['approvedAt'] is None and prompt['sourceTaskId'] is None
    assert prompt['imageHash'] == item['hash']
    assert len(prompt['promptHash']) == 64
    assert all(field not in item for field in ('storageKey', 'originalStorageKey', 'sourcePathLabel'))
    with catalog.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM character_assets').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM asset_images').fetchone()[0] == 0


def test_original_and_normalized_png_preserved(catalog):
    raw = image_bytes(fmt='JPEG')
    item = register(catalog, raw, mime='image/jpeg')
    assert catalog.file_path(item['candidateId'], 'original').read_bytes() == raw
    assert catalog.file_path(item['candidateId']).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert item['sourceHash'] != item['hash']
    assert item['originalMimeType'] == 'image/jpeg' and item['mimeType'] == 'image/png'


def test_legacy_import_is_v1_current_is_v2_and_original_path_never_read(catalog, tmp_path):
    current_path = tmp_path / 'replaced.png'
    current_path.write_bytes(image_bytes())
    old = history()
    old['path'] = str(current_path)
    previous = catalog.import_history(old, 'first-chibi-technical-validation')
    current = register(catalog, sourcePathLabel=str(current_path))
    assert previous['version'] == 1 and current['version'] == 2
    assert previous['filesAvailable'] is False
    assert current['sourceHash'] != previous['sourceHash']
    for kind in ('preview', 'original'):
        with pytest.raises(ServiceError) as exc:
            catalog.file_path(previous['candidateId'], kind)
        assert exc.value.code == 'CANDIDATE_FILE_UNAVAILABLE'
    old_bytes = catalog.file_path(current['candidateId']).read_bytes()
    current_path.write_bytes(image_bytes('#7755ff'))
    assert catalog.file_path(current['candidateId']).read_bytes() == old_bytes


def test_registration_idempotent_and_versions_do_not_overwrite(catalog):
    first = register(catalog)
    duplicate = register(catalog)
    newer = register(catalog, image_bytes('#aaccee'))
    assert duplicate == first
    assert newer['version'] == 2 and newer['candidateId'] != first['candidateId']
    assert catalog.get(first['candidateId']) == first
    assert catalog.file_path(first['candidateId']).read_bytes() != catalog.file_path(newer['candidateId']).read_bytes()
    assert len(catalog.list('first-chibi-technical-validation')) == 2


def test_history_idempotent_and_cannot_be_inserted_over_live_versions(catalog):
    old = catalog.import_history(history(), 'first-chibi-technical-validation')
    assert catalog.import_history(history(), 'first-chibi-technical-validation') == old
    changed = {**history(), 'sha256': '2' * 64}
    with pytest.raises(ServiceError) as exc:
        catalog.import_history(changed, 'first-chibi-technical-validation')
    assert exc.value.code == 'CANDIDATE_HISTORY_CONFLICT'


def test_atomic_parallel_duplicate_registration(catalog):
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda _: register(catalog), range(8)))
    assert len({item['candidateId'] for item in records}) == 1
    assert len(catalog.list()) == 1
    assert list(catalog.root.rglob('*.part')) == []


def test_atomic_parallel_distinct_versions(catalog):
    colors = ['#' + format(index + 10, '06x') for index in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(lambda color: register(catalog, image_bytes(color)), colors))
    assert {item['version'] for item in records} == set(range(1, 9))
    assert len({item['candidateId'] for item in records}) == 8


def test_candidates_survive_reopening_and_metadata_cannot_be_mutated(catalog):
    item = register(catalog)
    reopened = CandidateCatalog(catalog.assets)
    assert reopened.get(item['candidateId']) == item
    assert reopened.file_path(item['candidateId']).exists()
    for sql in ('UPDATE concept_candidates SET version=99', 'DELETE FROM concept_candidates'):
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            with reopened.store.connect() as db:
                db.execute(sql)


@pytest.mark.parametrize('candidate_id', ['../catalog.sqlite3', '..', 'file:///a', '', None, 'not-a-uuid'])
def test_uuid_only_no_arbitrary_path_read(catalog, candidate_id):
    with pytest.raises(ServiceError) as exc:
        catalog.get(candidate_id)
    assert exc.value.code == 'CANDIDATE_ID_INVALID'


@pytest.mark.parametrize('kind', ['preview', 'original'])
def test_changed_hash_file_rejected(catalog, kind):
    item = register(catalog)
    path = catalog.file_path(item['candidateId'], kind)
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ServiceError) as exc:
        catalog.file_path(item['candidateId'], kind)
    assert exc.value.code == 'CANDIDATE_FILE_CHANGED'


def test_changed_length_file_rejected(catalog):
    item = register(catalog)
    catalog.file_path(item['candidateId']).write_bytes(b'missing')
    with pytest.raises(ServiceError) as exc:
        catalog.file_path(item['candidateId'])
    assert exc.value.code == 'CANDIDATE_FILE_CHANGED'


def test_missing_private_snapshot_does_not_fallback_to_source_path(catalog):
    item = register(catalog)
    catalog.file_path(item['candidateId']).unlink()
    with pytest.raises(ServiceError) as exc:
        catalog.file_path(item['candidateId'])
    assert exc.value.code == 'CANDIDATE_FILE_UNAVAILABLE'


def test_caller_cannot_grant_prompt_approval_or_association(catalog):
    item = register(catalog, sourceNote={'verified': True, 'statement': '未经核实的调用者声明'},
                    licenseNote={'commercialUseVerified': True, 'statement': '仍未经核实'},
                    promptSnapshot={'version': 'v1', 'text': '仅离线候选', 'approved': True,
                                    'approvedAt': 'forged', 'characterId': 'forged',
                                    'sourceTaskId': 'forged', 'culturalApproval': True,
                                    'promptHash': 'forged'})
    assert item['sourceVerified'] is item['commercialUseVerified'] is False
    assert item['characterId'] is None
    assert item['promptSnapshot']['approved'] is False
    assert item['promptSnapshot']['approvedAt'] is None
    assert item['promptSnapshot']['characterId'] is None
    assert item['promptSnapshot']['culturalApproval'] is False
    assert item['promptSnapshot']['promptHash'] != 'forged'


@pytest.mark.parametrize('extras', [
    {'styleMode': 'unknown'}, {'scope': ''}, {'licenseNote': ''},
    {'promptSnapshot': {'version': 'v1'}}, {'promptSnapshot': {'text': 'missing version'}},
    {'raw': b'not an image'}, {'mime': 'text/plain'},
])
def test_invalid_candidate_input_rejected(catalog, extras):
    with pytest.raises(ServiceError):
        register(catalog, **extras)
    assert catalog.list() == []


def test_public_data_omits_private_historical_metadata(catalog):
    item = catalog.import_history(history(), 'history-only')
    assert 'historicalMetadata' not in item
    assert catalog.get(item['candidateId']) == item
    assert 'D:\\not-read' not in json.dumps(item)
