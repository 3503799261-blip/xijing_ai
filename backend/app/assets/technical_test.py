"""Internal one-shot technical input, never a confirmed cultural character.

This module freezes local candidates and stores completed model bytes. It has
no network, authorization endpoint, UsageManager, or alternate sender. The
caller must enforce the same admin/human approval and global ledger gates as
formal generation. Public evidence hashes are audit bindings, not proofs of
copyright permission or cultural correctness.
"""
import hashlib
import re

from ..errors import ServiceError
from ..providers.neural4d import parameters_for_style
from .candidates import CandidateCatalog
from .validation import normalize_image, validate_glb
from .visual_prompt import canonical_hash


ASSET_KIND = 'internal_technical_test'
PURPOSE = '技术验证'
FORMAL_FIELDS = ('characterId', 'assetId', 'sourceTaskId', 'sourceResultHash',
                 'citationHash', 'imageId', 'assetVersion')
UNGRANTED_FLAGS = ('cultureAlignmentVerified', 'publicationAllowed',
                   'licenseVerified', 'commercialUseVerified')


def fail(code, message, status=409):
    raise ServiceError(code, message, status)


def digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        fail('NEURAL4D_TECHNICAL_INPUT_INVALID', f'{label}须为真实记录的SHA-256。', 422)
    return value


def _freeze(assets, data, *, require_latest):
    if not isinstance(data, dict):
        fail('NEURAL4D_TECHNICAL_INPUT_INVALID', '技术验证输入须为字典。', 422)
    allowed = {'candidateId', 'candidateVersion', 'candidateScope', 'styleMode', 'styleVersion',
               'purpose', 'modelCount', 'parameters', 'assetKind', 'imageHash', 'sourceImageHash',
               'promptHash', 'promptVersion', 'authorizationEvidenceHash', 'permissionEvidenceHash',
               'internalUseOnly', 'visibility', 'action', 'estimatedCredits',
               *FORMAL_FIELDS, *UNGRANTED_FLAGS}
    if set(data) - allowed:
        fail('NEURAL4D_TECHNICAL_INPUT_INVALID', '技术验证含未声明字段，不能加入额外身份或文化授权。', 422)
    if (type(data.get('modelCount')) is not int or data['modelCount'] != 1
            or data.get('styleMode') != 'chibi' or data.get('purpose') != PURPOSE):
        fail('NEURAL4D_TECHNICAL_INPUT_INVALID', '本次内部验证仅允许Q版、用途技术验证、单模型。', 422)
    if (data.get('assetKind', ASSET_KIND) != ASSET_KIND
            or any(data.get(field) is not None for field in FORMAL_FIELDS)
            or any(field in data and data[field] is not False for field in UNGRANTED_FLAGS)
            or ('internalUseOnly' in data and data['internalUseOnly'] is not True)
            or ('visibility' in data and data['visibility'] != 'internal')):
        fail('NEURAL4D_TECHNICAL_IDENTITY_INVALID', '技术验证不能冒称正式角色、文化审校或公开使用许可。', 422)
    for field in ('sourceImageHash', 'imageHash', 'promptHash',
                  'authorizationEvidenceHash', 'permissionEvidenceHash'):
        digest(data.get(field), field)
    catalog = CandidateCatalog(assets)
    candidate = catalog.get(data.get('candidateId'))
    version = candidate.get('version')
    if (type(version) is not int or version < 2 or candidate.get('filesAvailable') is not True
            or candidate.get('styleMode') != 'chibi'
            or candidate.get('mimeType') != 'image/png'
            or any(candidate.get(field) is not None for field in FORMAL_FIELDS[:3])
            or any(candidate.get(field) is not False for field in
                   ('accepted', 'imageAccepted', 'modelEligible', 'cultureAlignmentVerified'))):
        fail('NEURAL4D_TECHNICAL_CANDIDATE_INVALID', '须使用v2及以上、仍独立未关联角色的Q版候选快照。', 409)
    if require_latest:
        # Do not use the capped public list: an unsent approval must observe
        # every immutable revision in its own scope, including >100 records.
        with assets.store.connect() as db:
            latest = db.execute('SELECT MAX(version) FROM concept_candidates WHERE scope=?',
                                (candidate['scope'],)).fetchone()[0]
        if latest != version:
            fail('NEURAL4D_APPROVAL_STALE', '同用途候选已有新版本，原未发送批准不能继续使用。')
    prompt = candidate.get('promptSnapshot')
    if (not isinstance(prompt, dict) or prompt.get('frozenForReview') is not True
            or prompt.get('approved') is not False or prompt.get('approvedAt') is not None
            or prompt.get('culturalApproval') is not False
            or prompt.get('characterId') is not None or prompt.get('sourceTaskId') is not None
            or prompt.get('styleMode') != 'chibi'
            or prompt.get('snapshotKind') != 'unassociated_candidate_only'):
        fail('NEURAL4D_TECHNICAL_PROMPT_INVALID', '候选Prompt不是有效的待审独立快照。')
    prompt_hash = digest(prompt.get('promptHash'), '候选Prompt Hash')
    if canonical_hash({key: value for key, value in prompt.items() if key != 'promptHash'}) != prompt_hash:
        fail('NEURAL4D_TECHNICAL_PROMPT_INVALID', '候选Prompt快照Hash不匹配，停止技术验证。')
    if (data['sourceImageHash'] != candidate.get('sourceHash')
            or data['imageHash'] != candidate.get('hash') or data['promptHash'] != prompt_hash
            or prompt.get('sourceHash') != candidate.get('sourceHash')
            or prompt.get('imageHash') != candidate.get('hash')):
        fail('NEURAL4D_INPUT_CHANGED', '技术验证概念图或Prompt Hash已变化。')
    if (('candidateVersion' in data and (type(data['candidateVersion']) is not int or data['candidateVersion'] != version))
            or ('styleVersion' in data and (type(data['styleVersion']) is not int or data['styleVersion'] != version))
            or ('promptVersion' in data and data['promptVersion'] != prompt.get('version'))
            or ('candidateScope' in data and data['candidateScope'] != candidate['scope'])):
        fail('NEURAL4D_INPUT_CHANGED', '技术验证候选或Prompt版本不一致。')
    png_path = catalog.file_path(candidate['candidateId'])
    original_path = catalog.file_path(candidate['candidateId'], 'original')
    png, original = png_path.read_bytes(), original_path.read_bytes()
    # CandidateCatalog verifies storage records and file hashes. Recheck bytes
    # actually read to bind this freeze even if a file changed between reads.
    if (hashlib.sha256(png).hexdigest() != data['imageHash']
            or hashlib.sha256(original).hexdigest() != data['sourceImageHash']):
        fail('NEURAL4D_INPUT_CHANGED', '候选快照读取期间发生变化，停止技术验证。')
    _, decoded = normalize_image(png, 'image/png')
    if (decoded['sourceHash'] != data['imageHash']
            or decoded['width'] != candidate.get('width') or decoded['height'] != candidate.get('height')):
        fail('NEURAL4D_TECHNICAL_CANDIDATE_INVALID', '概念图不是已登记的完整PNG尺寸。')
    parameters = parameters_for_style('chibi')
    if 'parameters' in data and data['parameters'] != parameters:
        fail('NEURAL4D_INPUT_CHANGED', '技术验证参数不能由调用者更改。')
    return {'assetKind': ASSET_KIND, 'candidateId': candidate['candidateId'],
            'candidateVersion': version, 'candidateScope': candidate['scope'],
            **{field: None for field in FORMAL_FIELDS},
            'styleMode': 'chibi', 'styleVersion': version, 'modelCount': 1,
            'purpose': PURPOSE, 'parameters': parameters,
            'imageHash': data['imageHash'], 'sourceImageHash': data['sourceImageHash'],
            'promptHash': prompt_hash, 'promptVersion': prompt['version'],
            'authorizationEvidenceHash': data['authorizationEvidenceHash'],
            'permissionEvidenceHash': data['permissionEvidenceHash'],
            'internalUseOnly': True, 'visibility': 'internal',
            **{field: False for field in UNGRANTED_FLAGS}}


def freeze_technical_candidate(assets, data):
    """Prepare the exact local input; this does not grant send rights."""
    return _freeze(assets, data, require_latest=True)


def _verified_payload(assets, payload, *, require_latest):
    current = _freeze(assets, payload, require_latest=require_latest)
    if canonical_hash(current) != canonical_hash(payload):
        fail('NEURAL4D_INPUT_CHANGED', '内部技术验证冻结信封已变化或字段不完整。')
    return current


def technical_image_path(assets, payload):
    """Verify the full frozen envelope before the shared sender reads PNG."""
    checked = _verified_payload(assets, payload, require_latest=True)
    return CandidateCatalog(assets).file_path(checked['candidateId'])


def register_technical_model(assets, payload, raw, provider_task_id):
    """Store an already-requested result; no promotion to a cultural role.

    Later candidate edits invalidate unsent approvals but do not erase a model
    that a previously frozen task has already generated. Completion therefore
    checks its exact historical snapshot while allowing a newer scope version.
    """
    checked = _verified_payload(assets, payload, require_latest=False)
    if (not isinstance(provider_task_id, str) or not provider_task_id.strip()
            or len(provider_task_id) > 200 or any(ord(c) < 32 for c in provider_task_id)):
        fail('NEURAL4D_RESPONSE_INVALID', '供应商模型标识无效。', 502)
    validation = validate_glb(raw)
    lineage_fields = ('assetKind', 'candidateId', 'candidateVersion', 'candidateScope',
                      'characterId', 'sourceTaskId', 'sourceResultHash', 'citationHash',
                      'imageId', 'assetVersion', 'styleMode', 'styleVersion',
                      'imageHash', 'sourceImageHash', 'promptHash', 'promptVersion',
                      'authorizationEvidenceHash', 'permissionEvidenceHash',
                      'internalUseOnly', 'visibility', *UNGRANTED_FLAGS)
    metadata = {'hash': validation['hash'], 'size': len(raw), 'format': 'glb',
                'origin': 'neural4d_technical_test', 'providerTaskId': provider_task_id,
                'purpose': PURPOSE, 'title': '内部非公开技术验证 · 非正式角色资产',
                'licenseNote': '输入许可尚未独立核实；仅内部非公开技术验证，不代表角色文化审校或公开/商业使用许可。',
                'validation': validation, 'frozenPayloadHash': canonical_hash(checked),
                **{field: checked[field] for field in lineage_fields}}
    # Preserve stronger lineage checks than add_file's generic completion guard.
    with assets.store.connect() as db:
        row = db.execute("SELECT content_json FROM asset_models WHERE json_extract(content_json,'$.providerTaskId')=?",
                         (provider_task_id,)).fetchone()
    if row:
        import json
        existing = json.loads(row[0])
        if (existing.get('origin') != metadata['origin']
                or existing.get('hash') != validation['hash']
                or existing.get('frozenPayloadHash') != metadata['frozenPayloadHash']):
            fail('MODEL_RESULT_CONFLICT', '同一供应商任务绑定不同技术输入或返回不同模型，请人工核查。')
        return assets.public_model(existing)
    metadata['storageKey'] = assets.save_bytes('models', raw, validation['hash'], 'glb')
    saved = assets.store.add_file('model', None, metadata)
    # If another completion won the provider-task unique insertion, verify its
    # complete frozen lineage too; generic add_file cannot compare candidate IDs.
    if saved.get('frozenPayloadHash') != metadata['frozenPayloadHash']:
        fail('MODEL_RESULT_CONFLICT', '并发任务结果的技术输入不一致，停止加载。')
    return assets.public_model(saved)
