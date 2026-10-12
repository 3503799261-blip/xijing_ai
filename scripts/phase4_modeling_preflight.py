"""Local read-only preparation. Never approves, reserves, queries or creates a model."""
import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def readonly(path):
    if not path.is_file():
        return None
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/phase4-modeling-preflight-local.json')
    args = parser.parse_args()
    from backend.app.config import Settings, WORKSPACE_ROOT
    settings = Settings()
    ledger = readonly(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    policy, attempts, operations = None, [], []
    if ledger is not None:
        try:
            ledger.execute('BEGIN')
            row = ledger.execute('SELECT historical_used,max_attempts,creation_halted,halt_code FROM neural4d_usage_policy').fetchone()
            policy = dict(row) if row else None
            for row in ledger.execute('SELECT attempt_id,provider_task_id,state,payload_json,reserved_at,started_at,updated_at FROM neural4d_creation_attempts ORDER BY reserved_at'):
                payload = json.loads(row['payload_json'])
                attempts.append({'attemptId': row['attempt_id'], 'providerTaskId': row['provider_task_id'],
                                 'state': row['state'], 'reservedAt': row['reserved_at'], 'startedAt': row['started_at'],
                                 'updatedAt': row['updated_at'],
                                 'frozen': {key: payload.get(key) for key in ('characterId', 'assetId', 'assetVersion', 'styleMode', 'styleVersion', 'imageHash', 'promptHash', 'purpose')}})
            operations = [dict(row) for row in ledger.execute('SELECT operation,is_mock,count(*) AS count FROM neural4d_operational_requests GROUP BY operation,is_mock')]
        finally:
            ledger.close()
    catalog = readonly(settings.rag_data_dir / 'assets/catalog.sqlite3')
    assets = []
    if catalog is not None:
        try:
            for row in catalog.execute('SELECT content_json FROM character_assets ORDER BY created_at,asset_id'):
                value = json.loads(row[0])
                assets.append({key: value.get(key) for key in ('characterId', 'assetId', 'sourceTaskId', 'name', 'styleMode', 'styleVersion', 'purpose')})
        finally:
            catalog.close()
    candidate_record = json.loads((ROOT / 'docs/evidence/test-results/phase4-concept-candidate.json').read_text('utf-8'))
    image_path = Path(candidate_record['path'])
    actual = {'exists': image_path.is_file(), 'hashMatchesRecorded': False}
    if image_path.is_file():
        raw = image_path.read_bytes()
        from PIL import Image
        with Image.open(image_path) as image:
            actual.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), width=image.width, height=image.height, format=image.format)
        actual['hashMatchesRecorded'] = actual['sha256'] == candidate_record['sha256']
    known = bool(policy and policy['historical_used'] is not None)
    unresolved = [row for row in attempts if row['state'] in ('UNKNOWN', 'PENDING_RECONCILIATION')]
    nonterminal = [row for row in attempts if row['state'] not in ('SUCCEEDED', 'FAILED')]
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'LOCAL_READ_ONLY_NO_SUPPLIER_CALLS',
              'globalLimit': 3, 'historicalUsageVerified': known,
              'historicalUsed': policy['historical_used'] if policy else None,
              'localOccupiedAttempts': len(attempts),
              'globalRemaining': 3 - policy['historical_used'] - len(attempts) if known else None,
              'permanentHalt': bool(policy and policy['creation_halted']),
              'oldTasks': attempts, 'unresolvedTaskCount': len(unresolved), 'nonterminalTaskCount': len(nonterminal),
              'supplierHistoryChecked': False, 'operationalRequests': operations,
              'configuration': {'keyConfigured': bool(settings.neural4d_api_key.get_secret_value()),
                                'adminTokenConfigured': len(settings.neural4d_admin_token.get_secret_value()) >= 24,
                                'generationEnabled': settings.neural4d_generation_enabled,
                                'protocolVerified': settings.neural4d_protocol_verified,
                                'estimatedCredits': settings.neural4d_expected_credits},
              'registeredLocalAssets': assets, 'candidateImageActual': actual,
              'candidateCharacterId': candidate_record.get('characterId'),
              'candidateSourceTaskId': candidate_record.get('sourceTaskId'),
              'candidateImageAccepted': candidate_record.get('imageAccepted') is True,
              'paidApiCallsThisCheck': 0,
              'submissionReadiness': 'NOT_READY_REQUIRES_HISTORY_CHARACTER_IMAGE_PROMPT_COST_AND_SINGLE_APPROVAL'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'historicalUsageVerified': known, 'remaining': report['globalRemaining'],
                      'localAttempts': len(attempts), 'oldUnresolvedTasks': len(unresolved),
                      'keyConfigured': report['configuration']['keyConfigured'],
                      'candidateHashMatches': actual['hashMatchesRecorded'], 'submissionReadiness': report['submissionReadiness']}))


if __name__ == '__main__':
    main()
