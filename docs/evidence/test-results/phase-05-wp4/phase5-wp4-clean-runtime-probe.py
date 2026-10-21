"""Probe the installed isolated interpreter without app imports or network."""
from pathlib import Path
import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone

root = Path('D:/京剧/.runtime/phase5-wp4')
output = root / 'cold-env-attempt03-runtime-verification.json'
if output.exists():
    raise SystemExit('Do not overwrite prior runtime evidence')
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
network_attempts = []
def denied_connect(*args, **kwargs):
    network_attempts.append('blocked')
    raise RuntimeError('Network disabled in runtime import probe')
socket.socket.connect = denied_connect
socket.create_connection = denied_connect
prefix = Path(sys.prefix).resolve()
started = time.perf_counter()
modules = [
    ('fastapi', 'fastapi'), ('uvicorn', 'uvicorn'),
    ('pydantic-settings', 'pydantic_settings'), ('httpx', 'httpx'),
    ('qdrant-client', 'qdrant_client'), ('sentence-transformers', 'sentence_transformers'),
    ('torch', 'torch'), ('numpy', 'numpy'), ('pytest', 'pytest'),
    ('Pillow', 'PIL'), ('portalocker', 'portalocker'),
]
result = {'at': datetime.now(timezone.utc).isoformat(),
          'pythonVersion': sys.version, 'includeSystemSitePackages': False,
          'venvConfig': (prefix / 'pyvenv.cfg').read_text(encoding='utf-8'),
          'outsideVenvSitePackagesOnSysPath': [True for item in sys.path
              if 'site-packages' in Path(item).parts
              and not Path(item).resolve().is_relative_to(prefix)],
          'imports': []}
for distribution, module_name in modules:
    item_started = time.perf_counter()
    try:
        module = importlib.import_module(module_name)
        module_path = Path(module.__file__).resolve()
        result['imports'].append({'distribution': distribution, 'version': metadata.version(distribution),
            'status': 'PASS', 'loadedFromThisVenv': module_path.is_relative_to(prefix),
            'elapsedSeconds': round(time.perf_counter() - item_started, 3)})
    except Exception as exc:
        result['imports'].append({'distribution': distribution, 'status': 'FAIL',
            'errorType': type(exc).__name__, 'elapsedSeconds': round(time.perf_counter() - item_started, 3)})
requirements = root / 'recovery-workspace/source/backend/requirements.txt'
result.update(elapsedSeconds=round(time.perf_counter() - started, 3),
              requirementsSha256=hashlib.sha256(requirements.read_bytes()).hexdigest(),
              installedDistributions=len(list(metadata.distributions())),
              blockedNetworkAttempts=len(network_attempts), providerRequests=0)
result['status'] = 'PASS' if (all(row['status'] == 'PASS' and row['loadedFromThisVenv']
                                for row in result['imports'])
                            and not result['outsideVenvSitePackagesOnSysPath']
                            and not network_attempts) else 'FAIL'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'venvConfig'}, ensure_ascii=True))
raise SystemExit(0 if result['status'] == 'PASS' else 1)
