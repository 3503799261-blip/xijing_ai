"""Actual clean venv installation attempt, pinned requirements, no providers."""
import json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone
root=Path('D:/京剧/.runtime/phase5-wp4'); target=root/'cold-env'
if target.exists(): raise SystemExit('Use a fresh isolated venv')
started=time.perf_counter(); subprocess.run([sys.executable,'-m','venv',str(target)],check=True)
env=os.environ.copy()
for k in list(env):
    if k.upper().startswith(('DEEPSEEK_','NEURAL4D_','PIP_')): env.pop(k,None)
env.update(PIP_CONFIG_FILE=os.devnull,PIP_INDEX_URL='https://pypi.org/simple',PIP_CACHE_DIR=str(root/'pip-cache'),PYTHONIOENCODING='utf-8')
cmd=[str(target/'Scripts/python.exe'),'-m','pip','install','--disable-pip-version-check','--retries','0','--timeout','20','-r',str(root/'recovery-workspace/source/backend/requirements.txt')]
with (root/'cold-install-output.txt').open('x',encoding='utf-8') as log:
    p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
result={'at':datetime.now(timezone.utc).isoformat(),'command':cmd,'exitCode':p.returncode,'elapsedSeconds':round(time.perf_counter()-started,3),'includeSystemSitePackages':False,'requirementsChanged':False,'providerRequests':0,'note':'All subprocess output saved; install outcome is not application cold-start outcome.'}
(root/'cold-install-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result));sys.exit(p.returncode)
