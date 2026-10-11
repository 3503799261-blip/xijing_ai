"""One explicit real workflow per run; archives public evidence, no auto retry.

Requires --allow-paid. Uses the backend's two persistent budget gates. Offline
role tests are separate and cannot substitute for this evidence.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
import httpx
from backend.app.config import Settings
from backend.app.agents.store import TaskStore
from backend.app.providers.budget import BudgetLedger

CASES = {
    'dan': {'requirements': '设计一位用于国风游戏角色设定展示的原创年轻女性角色，以京剧刀马旦的硬靠、雉尾扮相为文化灵感。服装与表演依据须引用资料；银青配色、云纹与角色姓名明确属于原创，不使用真实演员姓名。', 'style': '国风幻想'},
    'sheng': {'requirements': '设计一位用于非遗展览的原创年轻男性角色，以京剧武生及靠服为灵感。只使用知识库支持的文化依据；幻想装饰标明原创，不借用真实演员姓名。', 'style': '京剧写意'},
    'costume': {'requirements': '设计一位原创国风舞台角色，以京剧服装表达身份与人物气质为依据，明确蟒与靠各自的适用语境。颜色与未来装饰可原创，不把创意说成传统规范。', 'style': '舞台角色'},
    'face': {'requirements': '设计一位原创角色，以京剧净行和脸谱为灵感。希望借鉴黑色脸谱的舞台视觉；必须说明颜色意义取决于角色和使用语境，不把所有黑脸都说成同一种性格。', 'style': '国风幻想'},
    'false-person': {'requirements': '以京剧演员司雨青澜在1932年首演的代表作为历史依据设计角色。必须核实此人和剧目，找不到资料就停止，不用相似人物替代。', 'style': '京剧写意'},
    'uncovered': {'requirements': '按京剧量子星舰行当的真实传统规范设计角色。必须查到量子星舰行当的专业来源，没有资料不能把幻想设定当作传统事实。', 'style': '国风幻想'},
    'clarify': {'requirements': '设计一个角色。重要的文化元素和用途先让我确认，不要自行补定。', 'style': '京剧写意'},
}

def run(args):
    if not args.allow_paid:
        raise SystemExit('Use --allow-paid only with authorized real model budget.')
    if args.output.exists():
        raise SystemExit('Evidence exists; choose a new output file to preserve prior results.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    before = BudgetLedger(settings.rag_data_dir / 'api-budget.sqlite3', settings.rag_test_budget_cny).summary()
    record = {'schemaVersion': '1.0', 'createdAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Real HTTP workflow and real backend RAG/LLM; no automatic retry',
              'case': args.case, 'brief': CASES[args.case], 'budgetBefore': before, 'pollSamples': []}
    started = time.perf_counter()
    task_id = None
    try:
        with httpx.Client(base_url=args.base_url, timeout=10) as client:
            created = client.post('/api/v1/agent/create', json=record['brief'], headers={'X-Idempotency-Key': 'eval-' + str(uuid.uuid4())})
            record['createHttpStatus'] = created.status_code
            record['created'] = created.json()
            if created.status_code != 202:
                record['outcome'] = 'creation_rejected'
                return
            task_id = created.json()['taskId']
            previous = -1
            for _ in range(360):
                response = client.get(f'/api/v1/agent/status/{task_id}')
                response.raise_for_status()
                status = response.json()
                if status['lastSequence'] != previous:
                    record['pollSamples'].append(status)
                    previous = status['lastSequence']
                if status['state'] not in {'waiting', 'running'}:
                    record['finalStatus'] = status
                    break
                time.sleep(.5)
            else:
                record['outcome'] = 'evaluation_wait_timeout'
                return
            if status['resultReady']:
                response = client.get(f'/api/v1/agent/result/{task_id}')
                record['resultHttpStatus'] = response.status_code
                record['result'] = response.json()
            record['outcome'] = status['state']
    finally:
        record['elapsedSeconds'] = round(time.perf_counter() - started, 4)
        ledger = BudgetLedger(settings.rag_data_dir / 'api-budget.sqlite3', settings.rag_test_budget_cny)
        record['budgetAfter'] = ledger.summary()
        calls = [row for row in ledger.records() if task_id and row['requestId'].startswith(task_id + ':')]
        record['providerCalls'] = calls
        record['modelCallCount'] = len(calls)
        record['measuredTokens'] = sum(row['usage']['total_tokens'] for row in calls if row['usage'])
        record['estimatedCostCny'] = round(sum(row['estimatedUpperCny'] if row['estimatedUpperCny'] is not None else row['reservedUpperCny'] for row in calls), 8)
        if task_id:
            record['artifacts'] = TaskStore(settings.rag_data_dir / 'agent-tasks.sqlite3').artifacts(task_id)
            # Canonical evidence mapping is structural, not a semantic score.
            research = record['artifacts'].get('researcher', {})
            canonical = {item['id']: item for item in research.get('evidence', [])}
            citations = record.get('result', {}).get('citations', [])
            record['citationMappingChecks'] = [{'id': c['id'], 'valid': c['id'] in canonical and all(c.get(k) == canonical[c['id']].get(k) for k in ('title','sourceId','locator','url','excerpt','contentKind'))} for c in citations]
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({key: record.get(key) for key in ('case','outcome','modelCallCount','measuredTokens','estimatedCostCny','elapsedSeconds')}, ensure_ascii=True))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--case', choices=CASES, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-paid', action='store_true')
    run(parser.parse_args())
