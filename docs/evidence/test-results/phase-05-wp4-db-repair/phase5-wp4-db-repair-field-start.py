"""Start only the isolated 8011 field-copy with blank keys and outward guard."""
import argparse,hashlib,json,os,socket,subprocess,sys,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
BASE=Path('D:/京剧/.runtime/phase5-wp4-db-repair-field-01')
WORK=BASE/'workspace'
parser=argparse.ArgumentParser()
parser.add_argument('--run',required=True)
parser.add_argument('--wrong-root',action='store_true')
args=parser.parse_args()
assert args.run.replace('-','').isalnum()
OUT=BASE/args.run
assert not OUT.exists()
with socket.socket() as sock:
 assert sock.connect_ex(('127.0.0.1',8011))!=0,'8011 already owned; do not replace unknown process'
OUT.mkdir()
guard=OUT/'network-guard'
guard.mkdir()
(guard/'sitecustomize.py').write_text('''import sys,os,json,ctypes,sqlite3
from pathlib import Path
from urllib.parse import urlsplit,unquote
if os.name=='nt': ctypes.WinDLL('kernel32').SetConsoleCtrlHandler(None,False)
scope=Path(os.environ['WP4_FIELD_SCOPE']).resolve()
def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):
  value=args[1] if event=='socket.connect' else args[0]
  host=value[0] if isinstance(value,tuple) else value
  if host not in ('127.0.0.1','::1','localhost',None):
   with open(os.environ['WP4_NETWORK_AUDIT'],'a',encoding='utf8') as out:out.write(json.dumps({'blocked':True,'kind':'external-network','destination':'redacted'})+'\\n')
   raise RuntimeError('FIELD_EXTERNAL_NETWORK_DISABLED')
 elif event=='sqlite3.connect' and args[0]!=':memory:':
  value=args[0]
  if isinstance(value,str) and value.startswith('file:'):
   value=unquote(urlsplit(value).path)
   if len(value)>2 and value[0]=='/' and value[2]==':': value=value[1:]
  path=Path(value).resolve()
  if not path.is_relative_to(scope): raise RuntimeError('FIELD_NONISOLATED_SQLITE_BLOCKED')
sys.addaudithook(guard)
''',encoding='utf8')
env=os.environ.copy()
for key in list(env):
 if key.upper().startswith(('DEEPSEEK_','NEURAL4D_','RAG_','EMBEDDING_','AGENT_')):
  env.pop(key,None)
env.update(PYTHONPATH=str(guard),WP4_FIELD_SCOPE=str(WORK),WP4_NETWORK_AUDIT=str(OUT/'network-blocks.jsonl'),
 XIJING_ENV_FILE=str(WORK/'.private-config/.env'),DEEPSEEK_API_KEY='',NEURAL4D_API_KEY='',NEURAL4D_ADMIN_TOKEN='',
 NEURAL4D_GENERATION_ENABLED='false',NEURAL4D_PROTOCOL_VERIFIED='false',AGENT_WORKFLOW_ENABLED='false',
 HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
if args.wrong_root:env['RAG_DATA_DIR']=str(WORK/'.runtime/incorrect-missing-data')
python=Path('D:/京剧/京剧/.venv/Scripts/python.exe')
command=[str(python),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8011','--workers','1']
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
out=(OUT/'server-output.log').open('x',encoding='utf8');err=(OUT/'server-error.log').open('x',encoding='utf8')
process=subprocess.Popen(command,cwd=WORK/'source',env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NEW_CONSOLE,startupinfo=startup)
started=time.perf_counter()
def get(path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:8011'+path,timeout=4) as response:
   raw=response.read();status=response.status
 except urllib.error.HTTPError as error:
  raw=error.read();status=error.code
 return status,raw
result={'kind':'WP4_REPAIR_FIELD_ISOLATED_SERVER','atUtc':datetime.now(timezone.utc).isoformat(),
        'pid':process.pid,'command':command,'source':'current product snapshot in independent workspace',
        'mode':'wrong configured root' if args.wrong_root else 'existing isolated root',
        'keys':'blank, never copied source secrets','network':'external DNS/connect denied process-locally',
        'neural4dCalls':0,'paidCalls':0,'checks':[]}
healthy=False
for _ in range(180):
 if process.poll() is not None:break
 try:
  status,raw=get('/api/v1/health')
  if status==200:
   result['health']=json.loads(raw);healthy=True;break
 except (OSError,ValueError):pass
 time.sleep(.5)
result['httpReady']=healthy;result['readySeconds']=round(time.perf_counter()-started,3)
if healthy:
 for path in ['/api/v1/agent/history?page=1&pageSize=1','/api/v1/capabilities','/api/v1/assets/usage',
              '/api/v1/assets/models/1fa0b519-caf4-4009-aec2-f20b0f9a3523',
              *['/'+p+'.html' for p in ('index','history','roles','facial','music','gallery','video','about')]]:
  status,raw=get(path)
  row={'path':path,'status':status,'bytes':len(raw)}
  if path.startswith('/api/'):row['response']=json.loads(raw)
  result['checks'].append(row)
result['wrongRootExists']=(WORK/'.runtime/incorrect-missing-data').exists()
(OUT/'startup-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
out.close();err.close()
print(json.dumps({'httpReady':healthy,'pid':process.pid,'readySeconds':result['readySeconds'],
                 'mode':result['mode'],'checks':len(result['checks']),'wrongRootExists':result['wrongRootExists']}))
raise SystemExit(0 if healthy else 1)
