"""Read-only final Phase 4 asset/ledger audit. No HTTP or application imports.

SQLite opens use mode=ro/query_only. The only output is a new JSON evidence
file. Private credential fields are never parsed, retained or printed.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
import ast
import hashlib
import json
import os
import re
import sqlite3
import struct
import subprocess

import portalocker

WORK = Path('D:/京剧')
REPO = WORK / '京剧'
RUNTIME = WORK / '.runtime'
ASSETS = RUNTIME / 'xijing-ai/assets'
OUTPUT = REPO / 'docs/evidence/phase-04/final-acceptance/asset-ledger-readback.json'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@contextmanager
def connection(path):
    assert path.is_file(), 'Required existing database is missing'
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    try:
        yield db
    finally:
        db.close()


def guarded_glb(path, expected_hash, expected_size):
    assert path.is_file() and not path.is_symlink()
    assert ASSETS.resolve() in path.resolve().parents
    actual_hash, size = digest(path), path.stat().st_size
    with path.open('rb') as stream:
        header = struct.unpack('<4sII', stream.read(12))
    assert actual_hash == expected_hash and size == expected_size
    assert header == (b'glTF', 2, size)
    return {'sha256': actual_hash, 'sizeBytes': size, 'glbHeaderValid': True,
        'localOnly': True, 'relativeRuntimePath': path.relative_to(RUNTIME).as_posix()}


def generation_boolean_only():
    tree = ast.parse((REPO / 'backend/app/config.py').read_text('utf-8'))
    default = next(node.value.value for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id == 'neural4d_generation_enabled'
        and isinstance(node.value, ast.Constant))
    # Select only this nonsecret flag. Do not use Settings/dotenv to load keys.
    flag = re.compile(r'^\s*NEURAL4D_GENERATION_ENABLED\s*=\s*(.*?)\s*$')
    values = []
    env_path = Path(os.environ.get('XIJING_ENV_FILE', WORK / '.private-config/.env'))
    with env_path.open('r', encoding='utf-8-sig') as stream:
        for line in stream:
            if not line.lstrip().startswith('NEURAL4D_GENERATION_ENABLED'):
                continue
            match = flag.match(line)
            assert match, 'Invalid nonsecret generation flag'
            value = match.group(1).strip().strip('"\'').lower()
            assert value in ('true', 'false')
            values.append(value == 'true')
    assert len(values) <= 1, 'Duplicate generation flags require review'
    override = os.environ.get('NEURAL4D_GENERATION_ENABLED')
    if override is not None:
        assert override.lower() in ('true', 'false')
    effective = override.lower() == 'true' if override is not None else (values[0] if values else default)
    assert default is False and effective is False
    return {'codeDefaultEnabled': default, 'privateConfigEnabled': values[0] if values else default,
        'processEnvironmentOverridePresent': override is not None,
        'effectiveConfiguredEnabled': effective, 'credentialsParsed': False,
        'liveServerRuntimeQueried': False}


def lock_probe():
    path = RUNTIME / 'neural4d-usage.owner.lock'
    if not path.is_file():
        return {'existingLockFile': False, 'state': 'NOT_CHECKED_NO_EXISTING_LOCK', 'fileModified': False}
    # Existing Windows owner locks intentionally deny byte reads. Do not read
    # lock contents: use only a read-only fd for the nonblocking lock attempt.
    before = (path.stat().st_size, path.stat().st_mtime_ns)
    with path.open('rb') as stream:
        try:
            portalocker.lock(stream, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.exceptions.LockException:
            state = 'HELD_OR_NONBLOCKING_LOCK_REFUSED'
        else:
            portalocker.unlock(stream)
            state = 'FREE_NONBLOCKING_PROBE_ACQUIRED_AND_RELEASED'
    assert (path.stat().st_size, path.stat().st_mtime_ns) == before
    return {'existingLockFile': True, 'state': state, 'nonblocking': True,
        'existingFileOpenedReadOnly': True, 'fileModified': False,
        'deletedOrReplaced': False, 'ownerIdentityVerified': False,
        'lockContentsRead': False, 'sizeAndMtimeUnchanged': True}


def main():
    assert not OUTPUT.exists(), 'Preserve prior evidence: output already exists'
    with connection(RUNTIME / 'neural4d-usage.sqlite3') as db:
        policy = dict(db.execute('SELECT max_attempts,historical_used,creation_halted,halt_code '
            'FROM neural4d_usage_policy').fetchone())
        attempts = [dict(row) for row in db.execute('SELECT attempt_id,approval_id,purpose,state,'
            'provider_task_id,payload_json,payload_hash FROM neural4d_creation_attempts ORDER BY reserved_at')]
        approvals = [dict(row) for row in db.execute('SELECT approval_id,consumed_attempt_id,'
            'estimated_credits FROM neural4d_model_approvals')]
        operations = [dict(row) for row in db.execute('SELECT operation,is_mock,count(*) count,'
            'sum(coalesce(actual_credits,0)) credits FROM neural4d_operational_requests '
            'GROUP BY operation,is_mock ORDER BY operation,is_mock')]
    assert policy['max_attempts'] == 3 and policy['historical_used'] == 0
    assert len(attempts) == 2 and all(row['state'] == 'SUCCEEDED' for row in attempts)
    assert len(approvals) == 2 and all(row['consumed_attempt_id'] for row in approvals)
    for row in attempts:
        row['frozenPayload'] = json.loads(row.pop('payload_json'))
        assert canonical(row['frozenPayload']) == row['payload_hash']
        assert row['frozenPayload']['modelCount'] == 1
        assert next(a for a in approvals if a['approval_id'] == row['approval_id'])['consumed_attempt_id'] == row['attempt_id']
    with connection(ASSETS / 'catalog.sqlite3') as db:
        models = [json.loads(row[0]) for row in db.execute('SELECT content_json FROM asset_models')]
        characters = {row[0]: json.loads(row[1]) for row in db.execute('SELECT asset_id,content_json FROM character_assets')}
        images = {row[0]: json.loads(row[1]) for row in db.execute('SELECT image_id,content_json FROM asset_images')}
        frozen_approvals = {row[0]: json.loads(row[1]) for row in db.execute('SELECT approval_id,payload_json FROM neural4d_frozen_approvals')}
    real_models = [item for item in models if item.get('providerTaskId')]
    assert len(real_models) == 2
    bindings = [
        ('bb074c31-1905-45b6-b763-22d065ddc616', '8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885', 26600184),
        ('8735f32e-097e-488c-962f-f11e64af7741', '51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e', 18266484),
    ]
    records = []
    for index, (task, original_hash, original_size) in enumerate(bindings, 1):
        model = next(item for item in real_models if item['providerTaskId'] == task)
        attempt = next(row for row in attempts if row['provider_task_id'] == task)
        payload = attempt['frozenPayload']
        assert frozen_approvals[attempt['approval_id']] == payload
        assert re.fullmatch(r'models/[a-f0-9]{64}\.glb', model['storageKey'])
        item = {'generationNumber': index, 'modelId': model['modelId'], 'providerTaskId': task,
            'attemptId': attempt['attempt_id'], 'origin': model['origin'], 'styleMode': model['styleMode'],
            'original': guarded_glb(ASSETS / 'recovery-quarantine' / (original_hash + '.bin'), original_hash, original_size),
            'viewerCompatible': guarded_glb(ASSETS / model['storageKey'], model['hash'], model['size']),
            'assetId': model.get('assetId'), 'characterId': model.get('characterId'),
            'singleModelFrozenPayloadVerified': True, 'frozenPayloadHash': attempt['payload_hash'],
            'estimatedCreditsAtApproval': next(a for a in approvals if a['approval_id'] == attempt['approval_id'])['estimated_credits']}
        if index == 1:
            assert model['origin'] == 'neural4d_technical_test' and model['assetId'] is None
            assert model['internalUseOnly'] is True and model['publicationAllowed'] is False
            item.update(formalCharacterAssociation=False, formalAssociationAbsenceIsDesignLimitation=True,
                internalUseOnly=True, publicationAllowed=False, sourceImageHash=model['sourceImageHash'],
                promptVersion=model['promptVersion'], promptHash=model['promptHash'])
        else:
            asset, image = characters[model['assetId']], images[model['imageId']]
            assert asset['name'] == '绛绣·戏韵' and asset['styleMode'] == 'realistic'
            assert asset['characterId'] == model['characterId'] == image['characterId']
            assert payload['assetId'] == asset['assetId'] == image['assetId']
            assert payload['imageId'] == image['imageId'] and payload['imageHash'] == image['hash']
            assert payload['promptHash'] == image['promptHash'] == asset['visualPrompt']['promptHash']
            assert payload['sourceResultHash'] == model['sourceResultHash'] == asset['sourceResultHash']
            assert payload['citationHash'] == model['citationHash'] == asset['citationHash']
            with connection(RUNTIME / 'xijing-ai/agent-tasks.sqlite3') as db:
                task_row = db.execute('SELECT state,result_json FROM agent_tasks WHERE task_id=?', (asset['sourceTaskId'],)).fetchone()
                result = json.loads(task_row['result_json'])
                completed_steps = db.execute("SELECT count(*) FROM agent_steps WHERE task_id=? AND state='completed'", (asset['sourceTaskId'],)).fetchone()[0]
            assert task_row['state'] == 'completed' and result['userConfirmed'] and result['publicationAllowed']
            assert completed_steps == 4 and result['review']['verdict'] == 'pass' and result['uncertain'] is False
            item.update(formalCharacterAssociation=True, characterName=asset['name'], sourceTaskId=asset['sourceTaskId'],
                sourceTaskState=task_row['state'], roleUserConfirmed=True, rolePublicationAllowed=True,
                completedAgentSteps=completed_steps, cultureReviewVerdict=result['review']['verdict'],
                sourceResultHash=asset['sourceResultHash'], citationHash=asset['citationHash'],
                imageId=image['imageId'], imageHash=image['hash'], sourceImageHash=image['sourceHash'],
                visualPromptHash=payload['promptHash'], styleTemplateVersion=asset['visualPrompt']['styleTemplateVersion'],
                sourceRoleNeedsNoNewGeneration=True, permissionScope='User declared competition display/upload/3D derivative only; no commercial sales or public GLB redistribution audit')
        records.append(item)
    with connection(RUNTIME / 'xijing-ai/api-budget.sqlite3') as db:
        llm_calls = db.execute('SELECT count(*) FROM calls').fetchone()[0]
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'docs/evidence/phase-04', 'docs/prompts/phase-04', 'docs/reports'], cwd=REPO).decode('utf-8').split('\0')
    archive_files = [REPO / name for name in tracked if name and (REPO / name).is_file()]
    forbidden = {'.glb', '.gltf', '.jpg', '.jpeg', '.png', '.sqlite3', '.db', '.env', '.bin'}
    private_binaries = [path.relative_to(REPO).as_posix() for path in archive_files if path.suffix.lower() in forbidden]
    # Earlier Phase 4 licensed fixture screenshots are valid public evidence;
    # specifically exclude private generated model/concept bytes in new folders.
    new_asset_scope = [path for path in archive_files if '/modeling/' in path.as_posix()]
    assert not [path for path in new_asset_scope if path.suffix.lower() in forbidden]
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'reviewDateAsiaShanghai': '2026-10-17',
        'kind': 'ACTUAL_READ_ONLY_PHASE4_FINAL_ASSET_LEDGER_CHECK', 'conclusion': 'PASS',
        'databaseAccess': 'sqlite uri mode=ro with PRAGMA query_only=ON; no service initializers',
        'supplierApiCalls': 0, 'httpCalls': 0, 'llmCallsByAudit': 0, 'databaseWrites': 0,
        'maxAttempts': 3, 'historicalAttempts': 0, 'used': 2, 'remaining': 1,
        'attemptStates': {'SUCCEEDED': 2}, 'unknownOrReconciliationTasks': 0, 'unfinishedCreationTasks': 0,
        'unconsumedApprovals': 0, 'allModelCounts': [1, 1], 'creationHalted': bool(policy['creation_halted']),
        'operations': operations, 'realHttpRequestCount': sum(r['count'] for r in operations if not r['is_mock']),
        'recordedActualCredits': sum(r['credits'] for r in operations if not r['is_mock']), 'currentLlmCalls': llm_calls,
        'models': records, 'localFixtureModelCount': len(models) - len(real_models),
        'generationConfiguration': generation_boolean_only(), 'creationOwnerLock': lock_probe(),
        'archiveScope': {'trackedReportPromptEvidenceFiles': len(archive_files),
            'trackedModelingEvidenceFiles': len(new_asset_scope), 'privateModelOrConceptBytesInModelingEvidence': False,
            'legacyPublicImageEvidenceCount': len(private_binaries),
            'privateModelFilesCopiedByAudit': False},
        'auditHarnessCorrection': 'Initial attempt to hash the locked owner file was refused by Windows; no output or DB mutation occurred. Replaced lock-content read with existing read-only fd nonblocking lock probe and unchanged size/mtime checks.',
        'limitations': ['This readback does not rerun the browser or imply physical mobile acceptance.',
            'Role acceptance is distinct from model artistic acceptance and intellectual-property audit.',
            'The first model intentionally has no confirmed formal character association.',
            'No remaining quota is authorized for automatic use.']}
    assert record['realHttpRequestCount'] == 18 and record['recordedActualCredits'] == 60
    assert llm_calls == 107
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'outcome': 'PASS', 'used': 2, 'remaining': 1, 'modelsVerified': len(records),
        'realHttpRequestCount': record['realHttpRequestCount'], 'currentLlmCalls': llm_calls,
        'generationDefaultEnabled': record['generationConfiguration']['effectiveConfiguredEnabled'],
        'lockState': record['creationOwnerLock']['state'], 'output': str(OUTPUT)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
