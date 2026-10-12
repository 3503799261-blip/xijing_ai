"""Actual localhost GET checks only. No supplier, paid call or model mutation."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads((ROOT / 'docs/evidence/test-results/phase4-bluewhite-candidate-registration.json').read_text('utf-8'))
    current, old = registration['candidate'], registration['previousCandidate']
    base = 'http://127.0.0.1:8000'
    checks = []

    def get(path):
        try:
            with urlopen(base + path, timeout=15) as response:
                return response.status, dict(response.headers), response.read()
        except HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def check(name, ok, facts):
        checks.append({'name': name, 'passed': bool(ok), 'facts': facts})

    status, _, body = get('/api/v1/assets/candidates/' + current['candidateId'])
    item = json.loads(body)
    check('current_candidate_metadata', status == 200 and item['sourceHash'] == current['sourceHash']
          and item['hash'] == current['hash'] and item['modelEligible'] is False and item['sourceTaskId'] is None,
          {'status': status, 'candidateId': item.get('candidateId'), 'sourceHash': item.get('sourceHash'),
           'version': item.get('version'), 'modelEligible': item.get('modelEligible')})
    status, headers, body = get('/api/v1/assets/candidates/' + current['candidateId'] + '/file')
    digest = hashlib.sha256(body).hexdigest()
    check('png_content_and_cache_isolation', status == 200 and digest == current['hash']
          and 'no-store' in headers.get('cache-control', '').lower()
          and headers.get('etag') == '"' + current['hash'] + '"',
          {'status': status, 'sha256': digest, 'size': len(body), 'headers': headers})
    status, _, _ = get('/api/v1/assets/candidates/' + old['candidateId'] + '/file')
    check('old_bytes_not_falsely_restored', status == 404, {'status': status, 'oldSourceHash': old['sourceHash']})
    status, _, _ = get('/api/v1/assets/images/' + current['candidateId'] + '/file')
    check('candidate_is_not_formal_accepted_image', status == 404, {'status': status})
    status, _, body = get('/api/v1/assets/usage')
    usage = json.loads(body)
    check('creation_remains_locked', status == 200 and usage['realEnabled'] is False
          and usage['remaining_calls'] is None,
          {'status': status, 'realEnabled': usage.get('realEnabled'), 'globalRemaining': usage.get('remaining_calls')})
    status, headers, body = get('/api/v1/assets/candidates/' + current['candidateId'] + '/preview')
    html = body.decode('utf-8')
    check('preview_current_version_and_safe_headers', status == 200 and current['sourceHash'] in html
          and old['sourceHash'] not in html and "script-src 'none'" in headers.get('content-security-policy', '')
          and 'no-store' in headers.get('cache-control', ''), {'status': status, 'headers': headers})
    for page in ('index', 'history', 'roles', 'facial', 'music', 'video', 'gallery', 'about'):
        status, _, body = get('/' + page + '.html')
        check('original_page_' + page, status == 200 and body == (ROOT / (page + '.html')).read_bytes(), {'status': status})
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'ACTUAL_LOCAL_HTTP_GET_ONLY',
              'passed': sum(c['passed'] for c in checks), 'failed': sum(not c['passed'] for c in checks),
              'checks': checks, 'supplierApiCalls': 0, 'modelCreationAttempts': 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({'passed': report['passed'], 'failed': report['failed'], 'supplierApiCalls': 0}))
    sys.exit(bool(report['failed']))


if __name__ == '__main__':
    main()
