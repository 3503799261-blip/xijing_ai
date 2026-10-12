"""Actual loopback asset/API regression. No LLM or supplier requests."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8000'
ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = '3e8a0a55-f124-42a5-8265-7a7bb9b4d9d8'


def request(path, method='GET', body=None, headers=None):
    payload = json.dumps(body).encode() if body is not None else None
    combined = {'Content-Type': 'application/json', **(headers or {})}
    req = urllib.request.Request(BASE + path, data=payload, method=method, headers=combined)
    try:
        reply = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        reply = error
    data = reply.read()
    content_type = reply.headers.get('content-type', '')
    return {'status': reply.status, 'contentType': content_type, 'size': len(data),
            'cors': reply.headers.get('access-control-allow-origin'),
            'contentRange': reply.headers.get('content-range'),
            'json': json.loads(data) if 'json' in content_type else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/phase4-http-assets-local.json')
    args = parser.parse_args()
    results = []
    def check(name, response, passed):
        results.append({'name': name, 'passed': bool(passed), 'response': response})
    health = request('/api/v1/health')
    check('actual backend and local knowledge ready', health, health['status'] == 200
          and health['json'].get('status') == 'ready' and health['json'].get('knowledge') is True)
    caps = request('/api/v1/capabilities')
    check('assets/viewer ready; paid image/model unavailable', caps,
          caps['status'] == 200 and caps['json'].get('assetManagement') is True
          and caps['json'].get('modelViewer') is True and caps['json'].get('conceptImage') is False
          and caps['json'].get('imageToModel') is False)
    usage = request('/api/v1/assets/usage')
    original_real_requests = usage['json'].get('realHttpRequests')
    check('global cap fixed3, history unknown locks creation', usage,
          usage['status'] == 200 and usage['json']['max_calls'] == 3
          and usage['json']['history_verified'] is False and usage['json']['used_calls'] is None
          and usage['json']['remaining_calls'] is None and usage['json']['realEnabled'] is False)
    model = request('/api/v1/assets/models/' + MODEL_ID + '/file', headers={'Range': 'bytes=0-99'})
    check('registered actual GLB supports Range206', model,
          model['status'] == 206 and model['size'] == 100 and model['contentType'] == 'model/gltf-binary')
    for label, path, body, headers in [
        ('balance verification requires admin', '/api/v1/assets/neural4d/verify', {'action': 'verify_balance'}, {}),
        ('creation requires admin', '/api/v1/assets/model-tasks', {'approvalId': '00000000-0000-4000-8000-000000000000', 'modelCount': 1}, {'X-Idempotency-Key': 'offline-http-safety-check'}),
        ('second duplicate creation stays refused', '/api/v1/assets/model-tasks', {'approvalId': '00000000-0000-4000-8000-000000000000', 'modelCount': 1}, {'X-Idempotency-Key': 'offline-http-safety-check'}),
    ]:
        value = request(path, 'POST', body, headers)
        check(label, value, value['status'] == 403)
    invalid = request('/api/v1/assets/model-tasks', 'POST', {'approvalId': '00000000-0000-4000-8000-000000000000', 'modelCount': 2}, {'X-Idempotency-Key': 'offline-http-invalid-count'})
    check('modelCount2 fails validation before provider', invalid, invalid['status'] == 422)
    large = request('/api/v1/assets/characters', 'POST', {'unknown': 'x' * 9000})
    check('oversized JSON rejected before processing', large, large['status'] == 413)
    allowed = request('/api/v1/assets/usage', headers={'Origin': BASE})
    check('exact local CORS origin allowed', allowed, allowed['cors'] == BASE)
    forbidden = request('/api/v1/assets/usage', headers={'Origin': 'https://unapproved.invalid'})
    check('unapproved CORS origin denied', forbidden, forbidden['cors'] is None)
    search = request('/api/v1/knowledge/search', 'POST', {'question': '京剧的生旦净丑分别是什么？', 'topK': 3})
    check('existing real local RAG retrieval still works without LLM', search,
          search['status'] == 200 and len(search['json'].get('evidence', [])) > 0)
    end = request('/api/v1/assets/usage')
    check('safety probes changed no creation attempts or provider operations', end,
          end['status'] == 200 and end['json'].get('used_attempts') is None
          and sum(end['json'].get('attemptStates', {}).values()) == 0
          and type(original_real_requests) is int
          and end['json'].get('realHttpRequests') == original_real_requests)
    report = {'executedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'REAL_LOOPBACK_HTTP_NO_PAID_CALLS',
              'command': '.\\.venv\\Scripts\\python.exe scripts/phase4_http_smoke.py', 'results': results,
              'passed': sum(row['passed'] for row in results), 'failed': sum(not row['passed'] for row in results)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'failed': report['failed'], 'failedNames': [row['name'] for row in results if not row['passed']]}))
    return report['failed'] == 0


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
