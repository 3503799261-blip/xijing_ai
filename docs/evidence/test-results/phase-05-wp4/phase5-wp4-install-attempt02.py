"""Isolated, real dependency installation with retained private failure logs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('D:/京剧/.runtime/phase5-wp4')
TARGET = ROOT / 'cold-env-attempt02'
TEMP = ROOT / 'install-temp'
SOURCE = ROOT / 'recovery-workspace/source'

def safe_environment(temp=False):
    env = os.environ.copy()
    for key in list(env):
        if key.upper().startswith(('DEEPSEEK_', 'NEURAL4D_', 'PIP_')):
            env.pop(key, None)
    env.update(PIP_CONFIG_FILE=os.devnull,
               PIP_INDEX_URL='https://pypi.org/simple',
               PIP_CACHE_DIR=str(ROOT / 'pip-cache'),
               PYTHONIOENCODING='utf-8')
    if temp:
        env.update(TEMP=str(TEMP), TMP=str(TEMP), TMPDIR=str(TEMP))
    return env

def recorded_run(name, command, env):
    log_path = ROOT / f'{name}.private-output.txt'
    started = time.perf_counter()
    with log_path.open('x', encoding='utf-8') as log:
        process = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    text = log_path.read_text(encoding='utf-8', errors='replace')
    errors = [line for line in text.splitlines()
              if re.search(r'(?:ERROR:|PermissionError:|OSError:|ModuleNotFoundError:|\[WinError \d+\])', line)]
    redacted = []
    for line in errors[-8:]:
        line = re.sub(r'(?i)(?:https?://)[^\s\'\"]+', '[URL REDACTED]', line)
        line = re.sub(r'(?i)\bsk-[a-z0-9_-]+', '[KEY REDACTED]', line)
        line = re.sub(r'C:[\\/]Users[\\/][^\\/\s\'\"]+', 'C:/Users/<user> line)
        redacted.append(line)
    return {'command': command, 'exitCode': process.returncode,
            'elapsedSeconds': round(time.perf_counter() - started, 3),
            'privateOutputFile': log_path.name, 'redactedFailureLines': redacted}

def main():
    if TARGET.exists():
        raise SystemExit('Fresh attempt target already exists; do not overwrite')
    TEMP.mkdir(exist_ok=True)
    result = {'startedAt': datetime.now(timezone.utc).isoformat(),
              'includeSystemSitePackages': False, 'requirementsChanged': False,
              'providerRequests': 0, 'steps': []}
    result_path = ROOT / 'cold-install-attempt02-result.json'
    def save():
        result['updatedAt'] = datetime.now(timezone.utc).isoformat()
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    prior = ROOT / 'cold-env/Scripts/python.exe'
    result['steps'].append(recorded_run('cold-install-attempt01-ensurepip-diagnostic',
        [str(prior), '-m', 'ensurepip', '--upgrade', '--default-pip'], safe_environment(False)))
    save()
    result['steps'].append(recorded_run('cold-install-attempt02-venv',
        [sys.executable, '-m', 'venv', str(TARGET)], safe_environment(True)))
    save()
    if result['steps'][-1]['exitCode']:
        result['status'] = 'VENV_FAILED'; save(); print(json.dumps(result, ensure_ascii=True)); return 1
    command = [str(TARGET / 'Scripts/python.exe'), '-m', 'pip', 'install',
        '--disable-pip-version-check', '--retries', '0', '--timeout', '20',
        '-r', str(SOURCE / 'backend/requirements.txt')]
    result['steps'].append(recorded_run('cold-install-attempt02-pip', command, safe_environment(True)))
    result['status'] = 'INSTALLED' if not result['steps'][-1]['exitCode'] else 'INSTALL_FAILED'
    save()
    if result['status'] == 'INSTALLED':
        result['steps'].append(recorded_run('cold-install-attempt02-pip-check',
            [str(TARGET / 'Scripts/python.exe'), '-m', 'pip', 'check'], safe_environment(True)))
        result['steps'].append(recorded_run('cold-install-attempt02-pip-list',
            [str(TARGET / 'Scripts/python.exe'), '-m', 'pip', 'list', '--format=json'], safe_environment(True)))
        save()
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result['status'] == 'INSTALLED' else 1

if __name__ == '__main__':
    raise SystemExit(main())
