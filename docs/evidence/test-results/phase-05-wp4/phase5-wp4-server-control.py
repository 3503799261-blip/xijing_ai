"""Private WP4 start and free HTTP probes of the documented single-worker command."""
import argparse, hashlib, json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=8000);a=p.parse_args()
a.output.mkdir(exist_ok=False)
with socket.socket() as s: assert s.connect_ex(('127.0.0.1',a.port))!=0,'Identify existing port owner; never force replace'
guard=a.output/'network-guard';guard.mkdir()
(guard/'sitecustomize.py').write_text('''import sys, os, json, ctypes
from pathlib import Path
# Test-launcher only: do not inherit the orchestration shell's Ctrl+C-ignore bit.
if os.name == 'nt': ctypes.WinDLL('kernel32').SetConsoleCtrlHandler(None, False)
def guard(event,args):
    if event in ('socket.connect','socket.getaddrinfo'):
        value=args[1] if event=='socket.connect' else args[0]
        host=value[0] if isinstance(value,tuple) else value
        if host not in ('127.0.0.1','::1','localhost',None):
            with open(os.environ['WP4_NETWORK_AUDIT'],'a',encoding='utf-8') as f:f.write(json.dumps({'event':event,'blocked':True,'destination':'external-redacted'})+'\\n')
            raise RuntimeError('WP4_EXTERNAL_NETWORK_DISABLED')
sys.addaudithook(guard)
''',encoding='utf-8')
env=os.environ.copy();env.update(PYTHONPATH=str(guard),WP4_NETWORK_AUDIT=str(a.output/'network-blocks.jsonl'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
cmd=[str(a.python),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(a.port),'--workers','1']
started=time.perf_counter(); at=datetime.now(timezone.utc).isoformat()
startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
out=(a.output/'server-output.log').open('x',encoding='utf-8');err=(a.output/'server-error.log').open('x',encoding='utf-8')
process=subprocess.Popen(cmd,cwd=a.repo,env=env,stdout=out,stderr=err,creationflags=subprocess.CREATE_NEW_CONSOLE,startupinfo=startup)
result={'at':at,'command':cmd,'cwd':str(a.repo),'launcherPid':process.pid,'networkPolicy':'process-local audit denies external DNS/connect; no production config changed','consoleCtrlCEnabled':True,'checks':[]}
healthy=False
for _ in range(180):
    if process.poll() is not None: break
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{a.port}/api/v1/health',timeout=2) as r:health=json.load(r)
        healthy=True;break
    except (OSError,ValueError):time.sleep(.5)
result['httpReady']=healthy;result['readySeconds']=round(time.perf_counter()-started,3)
if healthy:
    result['health']=health
    for endpoint in ('/index.html','/about.html','/api/v1/capabilities','/api/v1/agent/history?page=1&pageSize=1','/api/v1/assets/usage','/api/v1/assets/models/1fa0b519-caf4-4009-aec2-f20b0f9a3523'):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{a.port}'+endpoint,timeout=10) as r: content=r.read();code=r.status
            record={'path':endpoint,'status':code,'sizeBytes':len(content)}
            if endpoint.startswith('/api/'): record['response']=json.loads(content)
            result['checks'].append(record)
        except Exception as e:result['checks'].append({'path':endpoint,'errorType':type(e).__name__})
result['elapsedSeconds']=round(time.perf_counter()-started,3)
(a.output/'startup-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');out.close();err.close()
print(json.dumps({'httpReady':healthy,'pid':process.pid,'readySeconds':result['readySeconds'],'checks':len(result['checks'])}));sys.exit(0 if healthy else 1)
