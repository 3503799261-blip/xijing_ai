"""WP3 invariant snapshot: sqlite mode=ro/query_only, no app/env/HTTP imports.

Writes only a new evidence JSON. Table hashes cover every persisted field and
record. JSON values are canonicalized; per-task summaries contain hashes and
controlled provenance signals, not user brief/artifact text or credentials.
"""
import argparse
import hashlib
import json
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / '.runtime'
REPO = ROOT / '京剧'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def parse(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def jsonhash(value):
    return None if value is None else sha(parse(value))


def tables(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    assert db.execute('PRAGMA query_only').fetchone()[0] == 1
    output, rows_by_table = {}, {}
    try:
        db.execute('BEGIN')
        for item in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            name, sql = item['name'], item['sql']
            assert name.replace('_', '').isalnum()
            records = [dict(row) for row in db.execute('SELECT * FROM "' + name + '"')]
            normalized = [{k: parse(v) if k.endswith('_json') else v for k, v in row.items()} for row in records]
            normalized.sort(key=canonical)
            columns = [dict(row) for row in db.execute('PRAGMA table_info("' + name + '")')]
            output[name] = {'count': len(records), 'canonicalSha256': sha(normalized),
                            'schemaSha256': sha(sql), 'columns': [c['name'] for c in columns],
                            'primaryKeyColumns': [c['name'] for c in sorted(columns, key=lambda c: c['pk']) if c['pk']]}
            rows_by_table[name] = records
        db.rollback()
    finally:
        db.close()
    return {'relativeRuntimeDatabase': path.relative_to(RUNTIME).as_posix(), 'tables': output,
            'databaseCanonicalSha256': sha(output), 'mode': 'ro', 'queryOnly': True}, rows_by_table


def tasks_summary(records):
    tasks = records['agent_tasks']
    steps = records['agent_steps']
    arts = records['agent_artifacts']
    events = records['agent_events']
    result = []
    for task in sorted(tasks, key=lambda row: row['task_id']):
        task_id = task['task_id']
        task_steps = sorted((s for s in steps if s['task_id'] == task_id), key=lambda s: s['agent_id'])
        task_arts = sorted((s for s in arts if s['task_id'] == task_id), key=lambda s: (s['agent_id'], s['version']))
        task_events = sorted((s for s in events if s['task_id'] == task_id), key=lambda s: s['sequence'])
        saved_result = parse(task['result_json']) or {}
        signals = []
        # These are suspicion indicators, not a claim that absence proves real execution.
        key = task['idempotency_key'].lower()
        for marker in ('test', 'mock', 'fixture', 'demo', 'smoke', 'eval', 'synthetic'):
            if marker in key:
                signals.append('idempotency-marker:' + marker)
        result.append({'taskId': task_id, 'state': task['state'], 'sequence': task['sequence'],
                       'createdAt': task['created_at'], 'updatedAt': task['updated_at'],
                       'briefSha256': jsonhash(task['brief_json']),
                       'confirmationSha256': jsonhash(task['confirmation_json']),
                       'resultSha256': jsonhash(task['result_json']),
                       'designSha256': sha(saved_result['design']) if saved_result.get('design') else None,
                       'reviewSha256': sha(saved_result['review']) if saved_result.get('review') else None,
                       'citationsSha256': sha(saved_result['citations']) if saved_result.get('citations') else None,
                       'reviewVerdict': (saved_result.get('review') or {}).get('verdict'),
                       'userConfirmed': saved_result.get('userConfirmed'),
                       'publicationAllowed': saved_result.get('publicationAllowed'),
                       'artifactCount': len(task_arts), 'eventCount': len(task_events),
                       'steps': [{'agentId': s['agent_id'], 'state': s['state'], 'startedAt': s['started_at'],
                                  'finishedAt': s['finished_at'], 'errorCode': s['error_code']} for s in task_steps],
                       'stepsSha256': sha(task_steps), 'artifactsSha256': sha(task_arts), 'eventsSha256': sha(task_events),
                       'eventSequences': [s['sequence'] for s in task_events],
                       'provenance': 'persisted_local_record_execution_origin_not_attested_by_schema',
                       'provenanceSignals': signals})
    return result


def models_summary(records):
    models = []
    for row in sorted(records['asset_models'], key=lambda r: r['model_id']):
        content = json.loads(row['content_json'])
        modelhash = content.get('hash')
        files = []
        for folder, filehash, suffix in [('models', modelhash, '.glb'),
                                         ('recovery-quarantine', content.get('originalHash'), '.bin')]:
            if not filehash:
                continue
            path = RUNTIME / 'xijing-ai/assets' / folder / (filehash + suffix)
            if not path.exists():
                files.append({'hash': filehash, 'exists': False})
                continue
            raw = path.read_bytes()
            magic, version, size = struct.unpack('<4sII', raw[:12])
            files.append({'relativeRuntimeAsset': path.relative_to(RUNTIME).as_posix(), 'exists': True,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'sizeBytes': len(raw),
                          'glbHeaderMatches': magic == b'glTF' and version == 2 and size == len(raw)})
            assert files[-1]['sha256'] == filehash
        models.append({'modelId': row['model_id'], 'assetId': row['asset_id'],
                       'contentSha256': jsonhash(row['content_json']), 'providerTaskId': content.get('providerTaskId'),
                       'origin': content.get('origin'), 'styleMode': content.get('styleMode'),
                       'internalUseOnly': content.get('internalUseOnly'), 'publicationAllowed': content.get('publicationAllowed'),
                       'files': files})
    return models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(RUNTIME) and not output.exists(), 'Use a fresh .runtime output'
    databases = {}
    agent, taskrows = tables(RUNTIME / 'xijing-ai/agent-tasks.sqlite3')
    databases['agents'] = agent
    catalog, catalogrows = tables(RUNTIME / 'xijing-ai/assets/catalog.sqlite3')
    databases['catalog'] = catalog
    usage, usagerows = tables(RUNTIME / 'neural4d-usage.sqlite3')
    databases['neural4dUsage'] = usage
    calls, callrows = tables(RUNTIME / 'xijing-ai/api-budget.sqlite3')
    databases['llmBudget'] = calls
    tasks = tasks_summary(taskrows)
    policy = usagerows['neural4d_usage_policy'][0]
    attempts = usagerows['neural4d_creation_attempts']
    operations = usagerows['neural4d_operational_requests']
    states = {}
    for item in tasks:
        states[item['state']] = states.get(item['state'], 0) + 1
    record = {'checkedAtUtc': datetime.now(timezone.utc).isoformat(), 'clientDate': '2026-10-19',
              'kind': 'WP3_READ_ONLY_COMPLETE_BUSINESS_INVARIANTS', 'credentialFilesRead': False,
              'appImported': False, 'httpRequests': 0, 'productionWrites': 0,
              'databases': databases, 'tasks': tasks, 'taskIds': sorted(t['taskId'] for t in tasks),
              'taskStates': states, 'liveTaskIds': [t['taskId'] for t in tasks if t['state'] in ('waiting', 'running')],
              'models': models_summary(catalogrows),
              'quota': {'maxAttempts': policy['max_attempts'], 'externalHistoricalUsed': policy['historical_used'],
                        'used': len(attempts) + policy['historical_used'],
                        'remaining': policy['max_attempts'] - len(attempts) - policy['historical_used'],
                        'attemptStates': [r['state'] for r in attempts],
                        'attemptCanonicalSha256': sha(attempts), 'policyCanonicalSha256': sha(usagerows['neural4d_usage_policy']),
                        'unconsumedApprovals': sum(r['consumed_attempt_id'] is None for r in usagerows['neural4d_model_approvals']),
                        'operationalRequestCount': len(operations),
                        'recordedCredits': sum(r.get('actual_credits') or 0 for r in operations)},
              'llmCalls': len(callrows['calls']),
              'htmlSha256': {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
                             for name in ('index.html','history.html','roles.html','facial.html','music.html','gallery.html','video.html','about.html')}}
    if args.compare:
        before = json.loads(args.compare.read_text('utf-8'))
        protected = ['databases', 'tasks', 'taskIds', 'taskStates', 'liveTaskIds', 'models', 'quota', 'llmCalls']
        record['comparison'] = {'beforeFile': args.compare.name,
                                'protectedFields': {k: before[k] == record[k] for k in protected},
                                'allProtectedUnchanged': all(before[k] == record[k] for k in protected),
                                'htmlChanged': [k for k,v in before['htmlSha256'].items() if record['htmlSha256'][k] != v]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    print(json.dumps({'output': output.as_posix(), 'taskCount': len(tasks), 'taskStates': states,
                      'tables': {k: {t: v['count'] for t,v in db['tables'].items()} for k,db in databases.items()},
                      'quota': record['quota'], 'llmCalls': record['llmCalls'], 'models': len(record['models']),
                      'comparison': record.get('comparison')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
