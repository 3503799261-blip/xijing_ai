"""Real explicit-init CLI in a new empty isolated root, with no credentials."""
from pathlib import Path
from datetime import datetime,timezone
import os,subprocess,json,hashlib
REPO=Path('D:/京剧/京剧')
ROOT=Path('D:/京剧/.runtime/phase5-wp4-db-repair-init-cli-01')
ROOT.mkdir(exist_ok=False)
empty=ROOT/'empty.env';empty.write_text('# No credentials or private configuration\n',encoding='utf8')
guard=ROOT/'guard';guard.mkdir()
(guard/'sitecustomize.py').write_text('''import os,sys
from pathlib import Path
from urllib.parse import urlsplit,unquote
root=Path(os.environ['WP4_INIT_SCOPE']).resolve()
def audit(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):raise RuntimeError('INITIALIZATION_NETWORK_FORBIDDEN')
 if event=='sqlite3.connect' and args[0]!=':memory:':
  value=args[0]
  if isinstance(value,str) and value.startswith('file:'):
   value=unquote(urlsplit(value).path)
   if len(value)>2 and value[0]=='/' and value[2]==':':value=value[1:]
  if not Path(value).resolve().is_relative_to(root):raise RuntimeError('INITIALIZATION_PRODUCTION_DB_FORBIDDEN')
sys.addaudithook(audit)
''',encoding='utf8')
env=os.environ.copy()
for key in list(env):
 if key.upper().startswith(('DEEPSEEK_','NEURAL4D_','RAG_','EMBEDDING_','AGENT_')):env.pop(key,None)
env.update(XIJING_ENV_FILE=str(empty),RAG_DATA_DIR=str(ROOT/'data'),EMBEDDING_MODEL_PATH=str(ROOT/'missing-model'),DEEPSEEK_API_KEY='',NEURAL4D_API_KEY='',NEURAL4D_ADMIN_TOKEN='',NEURAL4D_GENERATION_ENABLED='false',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(guard),WP4_INIT_SCOPE=str(ROOT))
cmd=[str(REPO/'.venv/Scripts/python.exe'),'-m','backend.scripts.initialize_business_databases']
def run(args,name):
 p=subprocess.run(cmd+args,cwd=REPO,env=env,text=True,encoding='utf8',capture_output=True,timeout=30)
 (ROOT/(name+'.stdout.txt')).write_text(p.stdout,encoding='utf8');(ROOT/(name+'.stderr.txt')).write_text(p.stderr,encoding='utf8')
 return p
refused=run([],'refused')
no_files=not(ROOT/'data').exists()
first=run(['--initialize-new-installation'],'first')
paths=list((ROOT/'data').rglob('*.sqlite3'))
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
second=run(['--initialize-new-installation'],'second')
same=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in hashes.items())
checks={'missingExplicitFlagRefused':refused.returncode==2,'refusalCreatesNothing':no_files,'firstExit0':first.returncode==0,'threeBusinessFiles':len(paths)==3,'firstStatesNew':set(json.loads(first.stdout)['stores'].values())=={'initialized_new'},'secondExit0':second.returncode==0,'existingStatesValidated':set(json.loads(second.stdout)['stores'].values())=={'validated_existing'},'repeatBytesUnchanged':same,'noNeuralLedger':not(ROOT/'data/neural4d-usage.sqlite3').exists()}
result={'kind':'REAL_EXPLICIT_INITIALIZATION_CLI','atUtc':datetime.now(timezone.utc).isoformat(),'commands':[cmd,cmd+['--initialize-new-installation']],'checks':checks,'passed':sum(checks.values()),'failed':sum(not x for x in checks.values()),'files':hashes,'paidApiCalls':0,'neural4dCalls':0,'productionDbAccess':'forbidden by child audit','network':'all forbidden'}
(ROOT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':result['passed'],'failed':result['failed']}))
raise SystemExit(0 if all(checks.values()) else 1)
