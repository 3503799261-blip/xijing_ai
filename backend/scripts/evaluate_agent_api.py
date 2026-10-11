"""Read/boundary HTTP checks and replay of an existing task; no new paid task."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import httpx
from backend.app.config import Settings
from backend.app.agents.store import TaskStore

def run(args):
    if args.output.exists(): raise SystemExit('Choose a new output path to retain evidence.')
    store=TaskStore(Settings().rag_data_dir/'agent-tasks.sqlite3')
    brief=store.brief(args.task_id)
    with store.connect() as db:
        key=db.execute('SELECT idempotency_key FROM agent_tasks WHERE task_id=?',(args.task_id,)).fetchone()[0]
    report={'executedAt':datetime.now(timezone.utc).isoformat(),'scope':__doc__,'checks':[]}
    with httpx.Client(base_url=args.base_url,timeout=10) as client:
        before=client.get('/api/v1/health').json()
        def check(name,method,path,expected,**kwargs):
            response=client.request(method,path,**kwargs)
            data=response.json()
            report['checks'].append({'name':name,'status':response.status_code,'expected':expected,'passed':response.status_code==expected,'response':data})
            return data
        check('real capabilities','GET','/api/v1/capabilities',200)
        check('real published sources','GET','/api/v1/knowledge/sources',200)
        check('real BGE search','POST','/api/v1/knowledge/search',200,json={'question':'刀马旦的扮相有哪些特点？','topK':5})
        check('existing task status','GET','/api/v1/agent/status/'+args.task_id,200)
        replay=check('persistent exact-key replay','POST','/api/v1/agent/create',202,json=brief,headers={'X-Idempotency-Key':key})
        report['checks'].append({'name':'replay retains task ID','passed':replay['taskId']==args.task_id})
        check('different brief same key','POST','/api/v1/agent/create',409,json={**brief,'requirements':'不同输入'},headers={'X-Idempotency-Key':key})
        check('empty brief','POST','/api/v1/agent/create',422,json={'requirements':' '},headers={'X-Idempotency-Key':'test-free-no-call'})
        check('overlong brief','POST','/api/v1/agent/create',422,json={'requirements':'戏'*1201},headers={'X-Idempotency-Key':'test-free-no-call'})
        check('unknown task','GET','/api/v1/agent/status/00000000-0000-0000-0000-000000000000',404)
        check('out-of-range cursor','GET','/api/v1/agent/status/'+args.task_id+'?afterSequence='+str(2**80),422)
        check('out-of-range mutation sequence','POST','/api/v1/agent/cancel/'+args.task_id,422,json={'expectedSequence':2**80})
        check('invalid confirmation','POST','/api/v1/agent/confirm/'+args.task_id,409,json={'confirmationId':'00000000-0000-0000-0000-000000000000','expectedSequence':store.status(args.task_id)['lastSequence'],'action':'accept'})
        after=client.get('/api/v1/health').json()
        report['checks'].append({'name':'all checks generate zero new model calls','passed':before['budget']['calls']==after['budget']['calls'],'before':before['budget']['calls'],'after':after['budget']['calls']})
        report['healthAfter']=after
    report['passed']=all(item['passed'] for item in report['checks'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'checks':len(report['checks'])}))
    return report['passed']

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--task-id',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(0 if run(args) else 1)
