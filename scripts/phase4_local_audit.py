"""Read-only local continuity/history audit; no API requests, no credential output."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WORKSPACE = ROOT.parent
BASELINE = 'c89e63e1f5afa575b5e3972dd5cfa26a897d3942'


def run(*args):
    return subprocess.check_output(args, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/phase4-continuity-local.json')
    args = parser.parse_args()
    pages = ['index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'video.html', 'gallery.html']
    continuity = []
    for page in pages:
        old = run('git', 'show', BASELINE + ':' + page)
        now = (ROOT / page).read_bytes()
        continuity.append({'path': page, 'identicalToPhase3': old == now, 'sha256': hashlib.sha256(now).hexdigest()})
    path = WORKSPACE / '.runtime/neural4d-usage.sqlite3'
    ledger = {'exists': path.exists(), 'externalSupplierHistoryVerified': False}
    if path.exists():
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        policy = db.execute('SELECT historical_used,max_attempts,creation_halted FROM neural4d_usage_policy').fetchone()
        ledger.update(historicalUsed=policy[0], maxAttempts=policy[1], creationHalted=bool(policy[2]),
                      localCreationAttempts=db.execute('SELECT count(*) FROM neural4d_creation_attempts').fetchone()[0],
                      localOperationalRequests=db.execute('SELECT operation,is_mock,count(*) FROM neural4d_operational_requests GROUP BY operation,is_mock').fetchall())
        db.close()
    from backend.app.config import Settings
    settings = Settings()
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'baseline': BASELINE,
              'branch': run('git', 'branch', '--show-current').decode().strip(),
              'head': run('git', 'rev-parse', 'HEAD').decode().strip(), 'culturalPages': continuity,
              'neural4d': ledger, 'keyConfigured': bool(settings.neural4d_api_key.get_secret_value()),
              'realCreationEnabled': settings.neural4d_generation_enabled,
              'conclusion': 'Local records cannot prove supplier/account-wide past attempts. User answered history uncertain; do not initialize it to zero. Creation remains locked pending supplier/manual reconciliation.'}
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
