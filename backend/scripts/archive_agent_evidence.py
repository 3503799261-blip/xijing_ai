"""Archive named public test tasks and non-secret usage; no model calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import httpx
from backend.app.config import Settings
from backend.app.agents.store import TaskStore
from backend.app.providers.budget import BudgetLedger


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main(args):
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    store = TaskStore(settings.rag_data_dir / 'agent-tasks.sqlite3')
    ledger = BudgetLedger(settings.rag_data_dir / 'api-budget.sqlite3', settings.rag_test_budget_cny)
    records = [item for item in ledger.records() if item['scope'] == 'phase3']
    now = datetime.now(timezone.utc).isoformat()
    usage = {key: sum(row['usage'].get(key, 0) for row in records if row['usage'])
             for key in ('prompt_tokens', 'completion_tokens', 'total_tokens',
                         'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens')}
    write(args.output / 'api-usage-final.json', {
        'generatedAt': now, 'scope': 'All provider calls attributed to Phase 3, including QA regression',
        'summary': ledger.summary(), 'usage': usage, 'records': records,
        'billingBoundary': 'Conservative application estimate; not account balance or provider hard cap',
        'phase2Baseline': {'calls': 62, 'estimatedUpperCostCny': 0.13343424}})
    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        tasks = []
        for task_id in args.task_id:
            response = client.get('/api/v1/agent/status/' + task_id)
            response.raise_for_status()
            status = response.json()
            task = {'taskId': task_id, 'status': status, 'artifacts': store.artifacts(task_id),
                    'providerCalls': [row for row in records if row['requestId'].startswith(task_id + ':')]}
            if status['resultReady']:
                response = client.get('/api/v1/agent/result/' + task_id)
                response.raise_for_status()
                task['result'] = response.json()
                evidence = {e['id']: e for e in task['artifacts']['researcher']['evidence']}
                task['citationMappingChecks'] = [{
                    'id': c['id'], 'valid': c['id'] in evidence and all(
                        c.get(k) == evidence[c['id']].get(k)
                        for k in ('title', 'sourceId', 'locator', 'url', 'excerpt', 'contentKind'))}
                    for c in task['result']['citations']]
            tasks.append(task)
        health = client.get('/api/v1/health'); health.raise_for_status()
        capabilities = client.get('/api/v1/capabilities'); capabilities.raise_for_status()
    write(args.output / 'browser-tasks-final.json', {
        'generatedAt': now, 'scope': 'Named actual public browser test tasks; no fabricated responses',
        'tasks': tasks, 'health': health.json(), 'capabilities': capabilities.json()})
    rows = []
    for path in sorted(args.output.glob('real-*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        status = data.get('finalStatus', {})
        result = data.get('result', {})
        rows.append({'file': path.name, 'case': data['case'], 'outcome': data.get('outcome'),
                     'reason': (status.get('confirmation') or {}).get('reason'),
                     'canAccept': (status.get('confirmation') or {}).get('canAccept', False),
                     'reviewVerdict': result.get('review', {}).get('verdict'),
                     'modelCallCount': data['modelCallCount'], 'tokens': data['measuredTokens'],
                     'estimatedCostCny': data['estimatedCostCny'], 'elapsedSeconds': data['elapsedSeconds'],
                     'mappingChecks': data.get('citationMappingChecks', []),
                     'promptVersions': result.get('promptVersions')})
    write(args.output / 'real-cases-summary.json', {
        'generatedAt': now, 'scope': 'All saved single-case real runs, including failures; not a blind accuracy metric',
        'cases': rows})
    if args.junit:
        suites = ET.parse(args.junit).getroot().findall('testsuite')
        write(args.output / 'backend-unit-final.json', {
            'generatedAt': now, 'scope': 'Offline pytest with explicit test doubles, not real model evidence',
            'command': '.venv/Scripts/python.exe -m pytest -q backend/tests --junitxml=<private-runtime-path>',
            'tests': sum(int(s.get('tests', 0)) for s in suites),
            'failures': sum(int(s.get('failures', 0)) for s in suites),
            'errors': sum(int(s.get('errors', 0)) for s in suites),
            'skipped': sum(int(s.get('skipped', 0)) for s in suites),
            'suiteSeconds': sum(float(s.get('time', 0)) for s in suites),
            'warning': 'Existing Starlette TestClient/httpx deprecation; no blocking failure'})
    print(json.dumps({'phase3Calls': len(records), 'tokens': usage['total_tokens'],
                      'budget': ledger.summary(), 'archivedTasks': len(tasks)}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', type=Path, default=Path('docs/evidence/test-results/phase-03'))
    parser.add_argument('--task-id', action='append', default=[])
    parser.add_argument('--junit', type=Path)
    main(parser.parse_args())
