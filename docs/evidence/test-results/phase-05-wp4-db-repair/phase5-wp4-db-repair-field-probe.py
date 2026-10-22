"""HTTP GET-only stage validation and readonly snapshot of isolated field files."""
import argparse,hashlib,json,sqlite3,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('D:/京剧/.runtime/phase5-wp4-db-repair-field-01')
WORK=BASE/'workspace'
parser=argparse.ArgumentParser()
parser.add_argument('--stage',choices=['corrupt','restored','misconfigured','recovered'],required=True)
args=parser.parse_args()
OUT=BASE/(args.stage+'-field-probe.json')
assert not OUT.exists()
preparation=json.loads((BASE/'preparation.json').read_text('utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8011'+path,timeout=10) as r:
   return r.status,r.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
def digest(path):
 result={}
 with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)as db:
  db.execute('PRAGMA query_only=ON')
  for name,sql in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
   assert name.replace('_','').isalnum()
   rows=db.execute('SELECT * FROM "'+name+'"').fetchall()
   result[name]={'count':len(rows),'schemaHash':hashlib.sha256(sql.encode()).hexdigest(),
                'rowsHash':hashlib.sha256(json.dumps(sorted(rows,key=repr),ensure_ascii=False,default=repr).encode()).hexdigest()}
 return result
responses={}
for path in ['/api/v1/health','/api/v1/agent/history?page=1&pageSize=50','/api/v1/assets/usage',
             *['/'+p+'.html' for p in ('index','history','roles','facial','music','gallery','video','about')]]:
 status,raw=get(path)
 responses[path]={'status':status}
 if path.startswith('/api/'):responses[path]['body']=json.loads(raw)
health=responses['/api/v1/health']['body']
history=responses['/api/v1/agent/history?page=1&pageSize=50']
dbfiles={name:{'sha256':sha(WORK/'.runtime'/row['relative']),
               'unchangedFromFieldInitial':sha(WORK/'.runtime'/row['relative'])==row['sha256']}
         for name,row in preparation['businessBaseline'].items()}
checks={'healthProcessAvailable':health['application']['available'] is True,
        'health200':responses['/api/v1/health']['status']==200,
        'eightPages200':all(responses['/'+p+'.html']['status']==200 for p in ('index','history','roles','facial','music','gallery','video','about')),
        'wrongRootNeverCreated':not(WORK/'.runtime/incorrect-missing-data').exists(),
        'budgetFileUnchanged':dbfiles['budget']['unchangedFromFieldInitial'],
        'catalogFileUnchanged':dbfiles['assets']['unchangedFromFieldInitial'],
        'quotaFileUnchanged':dbfiles['usage']['unchangedFromFieldInitial']}
if args.stage=='corrupt':
 checks.update(agentUnavailable=health['databases']['agent']['available'] is False,
               agentDiagnostic=health['databases']['agent']['diagnostic']=='AGENT_DATABASE_UNAVAILABLE',
               historySafe503=history['status']==503 and history['body'].get('error',{}).get('code')=='AGENT_DATABASE_UNAVAILABLE',
               corruptFileNotOverwritten=dbfiles['agents']['sha256']==preparation['isolatedAgentCorruptSha256'])
elif args.stage=='misconfigured':
 checks.update(agentUnavailable=health['databases']['agent']['available'] is False,
               budgetUnavailable=health['databases']['budget']['available'] is False,
               historySafe503=history['status']==503 and history['body'].get('error',{}).get('code')=='AGENT_DATABASE_UNAVAILABLE',
               existingOriginalAgentUntouched=dbfiles['agents']['sha256']==preparation['preservedValidAgentSha256'])
else:
 checks.update(agentAvailable=health['databases']['agent']['available'] is True,
               history22=history['status']==200 and history['body'].get('total')==22,
               restoredOriginalExact=dbfiles['agents']['sha256']==preparation['preservedValidAgentSha256'])
logical={name:digest(WORK/'.runtime'/row['relative'])for name,row in preparation['businessBaseline'].items()
         if name!='agents' or args.stage!='corrupt'}
result={'kind':'WP4_REPAIR_ISOLATED_FIELD_STAGE','atUtc':datetime.now(timezone.utc).isoformat(),
        'stage':args.stage,'checks':checks,'responses':responses,'fileHashes':dbfiles,'logicalTables':logical,
        'passed':sum(checks.values()),'failed':sum(not v for v in checks.values()),'skipped':0,
        'productionWrites':0,'paidApiCalls':0,'neural4dCalls':0,'scope':'real local isolated 8011 GET and readonly filesystem/SQLite'}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'stage':args.stage,'passed':result['passed'],'failed':result['failed'],'checks':checks},ensure_ascii=True))
raise SystemExit(0 if not result['failed'] else 1)
