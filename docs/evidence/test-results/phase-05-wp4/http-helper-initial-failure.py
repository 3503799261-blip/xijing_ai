"""Read persisted local routes; only allowed POST is free local knowledge search."""
import argparse, json, sqlite3, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
base=f'http://127.0.0.1:{a.port}';rows=[]
def request(path,body=None):
    if body is not None: assert path=='/api/v1/knowledge/search','Never call chat, agent or modeling'
    q=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'} if body is not None else {})
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(q,timeout=15) as r:code=r.status;raw=r.read()
    except urllib.error.HTTPError as e:code=e.code;raw=e.read()
    try:data=json.loads(raw)
    except ValueError:data=None
    return code,data,round(time.perf_counter()-started,5)
def check(name,path,expected,body=None,verify=lambda x:True):
    status,data,seconds=request(path,body);valid=status==expected and verify(data)
    rows.append({'name':name,'path':path,'method':'POST' if body is not None else 'GET','status': 'PASS' if valid else 'FAIL','httpStatus':status,'elapsedSeconds':seconds,'responseKeys':list(data) if isinstance(data,dict) else [],'errorCode':data.get('error',{}).get('code') if isinstance(data,dict) else None})
    return data
h=check('health_local_knowledge','/api/v1/health',200,verify=lambda d:d['knowledge'] and d['embedding'] and d['documents']==12 and d['chunks']==35)
check('capabilities_creation_closed','/api/v1/capabilities',200,verify=lambda d:d['knowledgeSearch'] and not d['imageToModel'] and not d['conceptImage'])
check('sources','/api/v1/knowledge/sources',200,verify=lambda d:len(d['sources'])==12)
r=check('real_cpu_vector_search','/api/v1/knowledge/search',200,{'question':'京剧主要使用哪两种声腔？','topK':5},lambda d:bool(d['evidence']) and not d['uncertain'])
check('invalid_empty_search','/api/v1/knowledge/search',422,{'question':''})
check('invalid_long_search','/api/v1/knowledge/search',422,{'question':'京'*601})
total=check('history_page_one','/api/v1/agent/history?page=1&pageSize=10',200,verify=lambda d:d['total']==22)
check('history_page_two','/api/v1/agent/history?page=2&pageSize=10',200,verify=lambda d:len(d['items'])==10)
check('history_completed_filter','/api/v1/agent/history?state=completed&page=1&pageSize=10',200,verify=lambda d:d['total']==2 and all(t['state']=='completed' for t in d['items']))
detail=check('saved_formal_role_details','/api/v1/agent/history/ca7007e7-e535-4b1f-a9b6-1932f10e20b4',200)
check('missing_history_404','/api/v1/agent/history/00000000-0000-4000-8000-000000000001',404)
check('global_ledger','/api/v1/assets/usage',200,verify=lambda d:d['used']==2 and d['remaining']==1 and not d['realEnabled'])
check('protected_backend','/backend/app/main.py',404)
check('protected_configuration','/.env',404)
report={'at':datetime.now(timezone.utc).isoformat(),'scope':'REAL_LOCAL_HTTP_NO_PAID_PROVIDERS','port':a.port,'checks':rows,'counts':{'pass':sum(r['status']=='PASS' for r in rows),'fail':sum(r['status']=='FAIL' for r in rows)},'modelGenerationRequests':0,'paidApiRequests':0,'liveLlmConnectivity':'NOT_TESTED','freeSearchEvidence':r,'savedHistoryResponseKeys':list(detail) if isinstance(detail,dict) else []}
a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report['counts']));raise SystemExit(0 if report['counts']['fail']==0 else 1)
