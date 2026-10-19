"""Local GET-only history acceptance against actual read-only SQLite, no providers."""
import argparse, hashlib, json, sqlite3, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists(): raise RuntimeError('Preserve existing evidence; choose a new output')
repo=Path.cwd();base='http://127.0.0.1:8000';checks=[];requests=[]
report={'kind':'WP2_ACTUAL_LOCAL_GET_AND_READONLY_SQLITE','startedAtUtc':datetime.now(timezone.utc).isoformat(),'checks':checks,'requests':requests,'paidCalls':0,'supplierCalls':0}
def check(name,ok,**meta):
    checks.append({'name':name,'passed':bool(ok),**meta})
    if not ok: raise AssertionError(name)
def get(path,expected=200):
    request=urllib.request.Request(base+path,headers={'Accept':'application/json'},method='GET');start=time.perf_counter()
    try:
        with urllib.request.urlopen(request,timeout=15) as response: code=response.status;raw=response.read();headers=response.headers
    except urllib.error.HTTPError as response: code=response.code;raw=response.read();headers=response.headers
    body=json.loads(raw);requests.append({'method':'GET','path':path,'status':code,'elapsedMs':round((time.perf_counter()-start)*1000,2)})
    check('HTTP '+path,code==expected)
    if '/agent/history' in path and code==200: check('history-no-store',headers.get('Cache-Control')=='no-store')
    return body
db=sqlite3.connect((repo.parent/'.runtime/xijing-ai/agent-tasks.sqlite3').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
try:
    rows=list(db.execute('SELECT task_id,state,created_at,result_json FROM agent_tasks ORDER BY created_at DESC,task_id DESC'))
    overview=get('/api/v1/agent/history?page=1&pageSize=5');seen=list(overview['items'])
    check('real-task-count',overview['total']==len(rows),taskCount=len(rows))
    for page in range(2,overview['totalPages']+1): seen.extend(get(f'/api/v1/agent/history?page={page}&pageSize=5')['items'])
    check('stable-page-order-and-no-duplicates',[v['taskId'] for v in seen]==[r['task_id'] for r in rows])
    check('summary-has-no-full-artifacts',all(not any(k in s for k in ['result','brief','artifacts','citations','culturalReview']) for s in seen))
    check('all-marked-readonly-history',overview['source']['readOnly'] and all(s['sourceType']=='persisted_history' for s in seen))
    for state in sorted(set(r['state'] for r in rows)):
        filtered=get('/api/v1/agent/history?pageSize=50&state='+state)
        check('status-filter-'+state,[v['taskId'] for v in filtered['items']]==[r['task_id'] for r in rows if r['state']==state])
    typed=get('/api/v1/agent/history?taskType=character_creation&pageSize=50')
    check('actual-single-task-type',typed['total']==len(rows) and all(t['taskType']=='character_creation' for t in typed['items']))
    missing='00000000-0000-0000-0000-000000000000'
    check('missing-id-list-empty',get('/api/v1/agent/history?taskId='+missing)['items']==[])
    get('/api/v1/agent/history/'+missing,404)
    get('/api/v1/agent/history?pageSize=51',422)
    check('unknown-state-empty-not-invented',get('/api/v1/agent/history?state=imaginary')['items']==[])
    check('unknown-type-empty-not-invented',get('/api/v1/agent/history?taskType=imaginary')['items']==[])
    for row in rows:
        task_id=row['task_id'];detail=get('/api/v1/agent/history/'+task_id+'?eventPageSize=2')
        check('stored-state-'+task_id,detail['task']['state']==row['state'] and detail['task']['taskId']==task_id)
        check('saved-agent-order-'+task_id,[a['id'] for a in detail['agents']]==['planner','researcher','designer','reviewer'])
        actual=db.execute('SELECT count(*) FROM agent_events WHERE task_id=?',(task_id,)).fetchone()[0]
        check('bounded-real-events-'+task_id,detail['eventTotal']==actual and len(detail['events'])==min(2,actual))
        check('missing-input-not-reconstructed-'+task_id,all('input' not in a or a['input'] is None for a in detail['agents']))
        stored=json.loads(row['result_json']) if row['result_json'] else None
        if stored and stored.get('design'):
            check('saved-design-name-'+task_id,detail['result']['design']['name']==stored['design']['name'])
        if task_id=='ca7007e7-e535-4b1f-a9b6-1932f10e20b4':
            assets=detail['assets'];match=[a for a in assets if a['assetId']=='9e2b42e1-bbad-4a2f-ab1b-aeda18015dee']
            check('realistic-role-model-association',len(match)==1 and match[0]['styleMode']=='realistic' and '1fa0b519-caf4-4009-aec2-f20b0f9a3523' in match[0]['modelIds'])
            check('internal-chibi-not-misassigned',all('3777a880-fc8c-4766-aade-948d20c6b8f0' not in a['modelIds'] for a in assets))
            report['showcase']={'taskId':task_id,'roleName':stored['design']['name'],'assetId':match[0]['assetId'],'modelIds':match[0]['modelIds']}
    sample=rows[0]['task_id'];page1=get('/api/v1/agent/history/'+sample+'?eventPage=1&eventPageSize=2');page2=get('/api/v1/agent/history/'+sample+'?eventPage=2&eventPageSize=2')
    check('detail-event-pagination',not set(e['sequence'] for e in page1['events'])&set(e['sequence'] for e in page2['events']))
    usage=get('/api/v1/assets/usage');report['usage']=usage
except Exception as error:
    report['failure']={'type':type(error).__name__,'message':str(error)[:200] if isinstance(error,AssertionError) else 'Local acceptance interrupted; inspect private trace without exposing secrets'}
finally:
    db.close();report['finishedAtUtc']=datetime.now(timezone.utc).isoformat();report['passed']=sum(c['passed'] for c in checks);report['failed']=sum(not c['passed'] for c in checks);report['skipped']=0
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps({'passed':report['passed'],'failed':report['failed'],'interrupted':'failure' in report,'requests':len(requests),'paidCalls':0}))
if report['failed'] or 'failure' in report:raise SystemExit(1)
