"""Temporarily hide ONLY the recovered GLB, with timed restoration in finally.

Explicit browser error test; no network, supplier, quota or database mutation.
"""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent / '.runtime'
MODEL_HASH = 'bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a'
target = ROOT / 'xijing-ai/assets/models' / (MODEL_HASH + '.glb')
backup = target.with_suffix('.glb.recovery-browser-test-backup')
release = ROOT / 'recovery-browser-test-release.signal'
report = ROOT / 'recovery-browser-error-fixture.json'
for path in (target, backup):
    if path.is_symlink() or path.resolve().parent != (ROOT / 'xijing-ai/assets/models').resolve():
        raise RuntimeError('Unexpected controlled model path')
if backup.exists() or release.exists() or not target.is_file():
    raise RuntimeError('Unexpected fixture state; no overwrite')
if hashlib.sha256(target.read_bytes()).hexdigest() != MODEL_HASH:
    raise RuntimeError('Original model hash mismatch')
state = {'kind': 'ACTUAL_LOCAL_GLBFILENOTFOUND_BROWSER_FIXTURE', 'hashBefore': MODEL_HASH,
         'databaseChanges': 0, 'supplierRequests': 0, 'timeoutRestorationSeconds': 60}
try:
    target.rename(backup)
    print('CONTROLLED_ORIGINAL_GLB_TEMPORARILY_MISSING', flush=True)
    until = time.monotonic() + 60
    while not release.exists() and time.monotonic() < until:
        time.sleep(0.1)
finally:
    if target.exists() or not backup.is_file() or backup.is_symlink():
        raise RuntimeError('Unexpected restore state; do not overwrite')
    backup.rename(target)
    state['hashAfter'] = hashlib.sha256(target.read_bytes()).hexdigest()
    state['restored'] = state['hashAfter'] == MODEL_HASH
    if release.is_file():
        release.unlink()
    report.write_text(json.dumps(state, indent=2)+'\n', 'utf-8')
    print(json.dumps(state), flush=True)
