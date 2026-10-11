"""Explicit local missing-resource browser test; no provider or credential use."""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings
from backend.app.agents.store import TaskStore
from backend.app.assets.service import AssetService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'missing', 'restore'])
    args = parser.parse_args()
    settings = Settings()
    service = AssetService(settings, TaskStore(settings.rag_data_dir / 'agent-tasks.sqlite3'))
    raw = (ROOT / 'backend/tests/fixtures/phase4/Duck.glb').read_bytes()
    length, kind = struct.unpack_from('<II', raw, 12)
    document = json.loads(raw[20:20 + length])
    document['extras'] = {**document.get('extras', {}), 'xijingTestPurpose': 'explicit_missing_resource_browser_test'}
    body = json.dumps(document, ensure_ascii=True, separators=(',', ':')).encode()
    body += b' ' * ((-len(body)) % 4)
    remainder = raw[20 + length:]
    marked = struct.pack('<III', 0x46546c67, 2, 20 + len(body) + len(remainder)) + struct.pack('<II', len(body), kind) + body + remainder
    import hashlib
    digest = hashlib.sha256(marked).hexdigest()
    model = next((row for row in service.list_models() if row['hash'] == digest and row['origin'] == 'local_test_fixture'), None)
    if model is None:
        if args.action == 'restore':
            raise RuntimeError('No registered failure fixture to restore.')
        model = service.register_fixture(marked,
            'Khronos Duck; Sony 2006; SCEA Shared Source License1.0 retained. Only GLB extras changed to identify a local failure test; not a role or generated asset.',
            'Duck · 临时缺失资源测试（非角色、非生成）')
    item = service.store.file('model', model['modelId'])
    target = (service.root / item['storageKey']).resolve()
    backup = target.with_suffix('.glb.browser-test-backup')
    for path in (target, backup):
        if service.root not in path.resolve().parents or path.parent != service.root / 'models':
            raise RuntimeError('Test path escaped registered private model storage.')
    if args.action == 'missing':
        if backup.exists() or not target.exists():
            raise RuntimeError('Unexpected fixture state; do not overwrite files.')
        target.rename(backup)
    elif args.action == 'restore':
        if target.exists() or not backup.exists():
            raise RuntimeError('Unexpected restore state; no files changed.')
        backup.rename(target)
    report = {**model, 'action': args.action, 'filePresent': target.is_file(), 'backupPresent': backup.is_file(),
              'paidApiCalls': 0, 'disclaimer': 'Local resource-failure test, no Neural4D generation.'}
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
