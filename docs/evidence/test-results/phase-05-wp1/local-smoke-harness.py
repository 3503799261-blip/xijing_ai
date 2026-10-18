"""WP1 bounded loopback GET and local-only knowledge search. No LLM/create route."""
from pathlib import Path
from datetime import datetime, timezone
import json, sqlite3, time
import httpx

repo=Path('D:/京剧/京剧'); work=repo.parent
output=repo/'docs/evidence/test-results/phase-05-wp1/local-smoke.json'
assert not output.exists()
record={'startedAtUtc':datetime.now(timezone.utc).isoformat(),'kind':'WP1_REAL_LOCAL_HTTP_AND_BGE_SEARCH','supplierCalls':0,'llmRequests':0,'modelCreationRequests':0,'checks':[]}
def check(name, passed, **extra):
    record['checks'].append({'name':name,'passed':bool(passed),**extra})
with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,follow_redirects=False,timeout=35) as client:
    for name,path in [('health','/api/v1/health'),('capabilities','/api/v1/capabilities'),('usage','/api/v1/assets/usage')]:
        response=client.get(path); response.raise_for_status(); data=response.json()
        if name=='health': check(name,data['knowledge'] and data['embedding'],httpStatus=response.status_code,status=data['status'],documents=data['documents'],chunks=data['chunks'],meaning='Local cached provider readiness, not a paid connectivity probe')
        elif name=='capabilities': check(name,data['imageToModel'] is False and data['modelViewer'] is True,capabilities=data)
        else: check(name,data['used_attempts']==2 and data['remaining_attempts']==1 and data['realEnabled'] is False,used=data['used_attempts'],remaining=data['remaining_attempts'],realEnabled=data['realEnabled'],realHttpRequests=data['realHttpRequests'])
    sources=client.get('/api/v1/knowledge/sources'); sources.raise_for_status()
    check('published-sources',len(sources.json()['sources'])==12,sourceCount=len(sources.json()['sources']))
    started=time.perf_counter()
    # This exact route only performs local BGE/Qdrant/SQLite retrieval.
    result=client.post('/api/v1/knowledge/search',json={'question':'京剧主要使用哪两种声腔？','topK':5})
    elapsed=time.perf_counter()-started; result.raise_for_status(); evidence=result.json()
    active=json.loads((work/'.runtime/xijing-ai/active.json').read_text('utf-8'))
    generation=active['generation_id']; assert generation.startswith('gen-') and '/' not in generation and '\\' not in generation
    database=work/'.runtime/xijing-ai/generations'/generation/'knowledge.sqlite3'
    validated=[]
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        for item in evidence['evidence']:
            row=db.execute('SELECT c.data_json,s.data_json FROM chunks c JOIN sources s USING(source_id) WHERE chunk_id=?',(item['id'],)).fetchone()
            assert row
            chunk,source=json.loads(row[0]),json.loads(row[1])
            ok=item['sourceId']==chunk['source_id']==source['source_id'] and item['excerpt']==chunk['content'] and item['title']==source['title'] and item['url']==source['source_url']
            validated.append({'id':item['id'],'sourceId':item['sourceId'],'canonicalFieldsMatch':ok})
    check('real-local-search-and-canonical-evidence',bool(evidence['evidence']) and not evidence['uncertain'] and all(v['canonicalFieldsMatch'] for v in validated),httpStatus=result.status_code,elapsedSeconds=round(elapsed,6),evidence=evidence,canonicalChecks=validated)
    invalid=client.post('/api/v1/knowledge/search',json={'question':' '})
    check('empty-search-validation',invalid.status_code==422,httpStatus=invalid.status_code,error=invalid.json())
    task='ca7007e7-e535-4b1f-a9b6-1932f10e20b4'
    status=client.get('/api/v1/agent/status/'+task); status.raise_for_status(); data=status.json()
    check('read-existing-agent-status',data['state']=='completed' and data['completedSteps']==4,taskId=task,state=data['state'],completedSteps=data['completedSteps'],createdAt=data['createdAt'],updatedAt=data['updatedAt'],meaning='Historical stored task; not rerun')
    response=client.get('/api/v1/agent/result/'+task); response.raise_for_status(); data=response.json()
    check('read-existing-accepted-role',data['userConfirmed'] and data['publicationAllowed'] and data['review']['verdict']=='pass',taskId=task,characterName=data['design']['name'],userConfirmed=data['userConfirmed'],publicationAllowed=data['publicationAllowed'],reviewVerdict=data['review']['verdict'],meaning='Historical result; no confirmation mutation')
record['finishedAtUtc']=datetime.now(timezone.utc).isoformat()
record['passed']=sum(c['passed'] for c in record['checks']);record['failed']=sum(not c['passed'] for c in record['checks']);record['skipped']=0
output.parent.mkdir(parents=True,exist_ok=True)
with output.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:record[k] for k in ['passed','failed','skipped','supplierCalls','llmRequests','modelCreationRequests']}))
raise SystemExit(1 if record['failed'] else 0)

