"""Retry normal isolated venv after recorded sandbox ensurepip denial; no providers."""
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from datetime import datetime, timezone
import json
import sys

spec = spec_from_file_location('wp4_install_tools', 'D:/京剧/.runtime/phase5-wp4-install-attempt02.py')
helper = module_from_spec(spec)
spec.loader.exec_module(helper)
root = helper.ROOT
target = root / 'cold-env-attempt03'
if target.exists():
    raise SystemExit('Fresh attempt target already exists; do not overwrite')
helper.TEMP.mkdir(exist_ok=True)
result = {'startedAt': datetime.now(timezone.utc).isoformat(),
          'attempt': 3, 'includeSystemSitePackages': False,
          'requirementsChanged': False, 'providerRequests': 0,
          'networkPurpose': 'official PyPI and CPU package-index dependency installation only',
          'steps': []}
result_path = root / 'cold-install-attempt03-result.json'
def save():
    result['updatedAt'] = datetime.now(timezone.utc).isoformat()
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
def run(name, command):
    result['steps'].append(helper.recorded_run(name, command, helper.safe_environment(True)))
    save()
    return result['steps'][-1]['exitCode']
if run('cold-install-attempt03-venv', [sys.executable, '-m', 'venv', str(target)]):
    result['status'] = 'VENV_FAILED'; save(); print(json.dumps(result, ensure_ascii=True)); raise SystemExit(1)
print(json.dumps({'event': 'venv_ready', 'target': str(target)}, ensure_ascii=True), flush=True)
cmd = [str(target / 'Scripts/python.exe'), '-m', 'pip', 'install',
       '--disable-pip-version-check', '--retries', '0', '--timeout', '20',
       '--index-url', 'https://pypi.org/simple',
       '-r', str(helper.SOURCE / 'backend/requirements.txt')]
code = run('cold-install-attempt03-pip', cmd)
result['status'] = 'INSTALLED' if code == 0 else 'INSTALL_FAILED'
save()
if not code:
    run('cold-install-attempt03-pip-check', [str(target / 'Scripts/python.exe'), '-m', 'pip', 'check'])
    run('cold-install-attempt03-pip-list', [str(target / 'Scripts/python.exe'), '-m', 'pip', 'list', '--format=json'])
    run('cold-install-attempt03-runtime-probe', [str(target / 'Scripts/python.exe'), '-c',
        'import json,sys,importlib.metadata as m; print(json.dumps({"version":sys.version,"prefix":sys.prefix,"basePrefix":sys.base_prefix,"basePackagesOnSysPath":any(p.endswith("Lib\\\\site-packages") and not p.startswith(sys.prefix) for p in sys.path),"versions":{n:m.version(n) for n in ["fastapi","uvicorn","pydantic-settings","httpx","qdrant-client","sentence-transformers","torch","numpy","pytest","Pillow","portalocker"]}}))'])
print(json.dumps(result, ensure_ascii=True), flush=True)
raise SystemExit(code)
