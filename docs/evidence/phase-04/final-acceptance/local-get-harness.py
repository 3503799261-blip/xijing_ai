"""Bounded local GET-only closeout; no supplier or model generation endpoints."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, httpx, subprocess

repo = Path('D:/京剧/京剧')
out = repo / 'docs/evidence/phase-04/final-acceptance'
out.mkdir(parents=True, exist_ok=True)
report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'LOCAL_GET_ONLY_FINAL_READBACK', 'supplierCalls': 0, 'paidCalls': 0, 'requests': []}
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=20, trust_env=False, follow_redirects=False) as client:
    for name in ['health', 'capabilities', 'assets/usage']:
        response = client.get('/api/v1/' + name)
        response.raise_for_status()
        body = response.json()
        if name == 'capabilities':
            report['capabilities'] = body
            assert body['imageToModel'] is False and body['modelViewer'] is True and body['conceptImage'] is False
        elif name == 'assets/usage':
            report['usage'] = body
            assert body['used_attempts'] == 2 and body['remaining_attempts'] == 1
        else:
            report['health'] = {'status': body.get('status')}
        report['requests'].append({'path': '/api/v1/' + name, 'method': 'GET', 'status': response.status_code})
    # Browser navigation can cancel streaming media; a bounded Range read checks availability.
    for path in ['/media/opera-audio.mp3', '/media/video1.mp4', '/media/video2.mp4', '/media/video3.mp4', '/media/video4.mp4', '/api/v1/assets/models/3777a880-fc8c-4766-aade-948d20c6b8f0/file']:
        with client.stream('GET', path, headers={'Range': 'bytes=0-1023'}) as response:
            data = b''.join(response.iter_bytes())
            assert response.status_code == 206 and len(data) == 1024
            report['requests'].append({'path': path, 'method': 'GET', 'status': response.status_code, 'bytesReceived': len(data), 'contentRange': response.headers.get('Content-Range')})
    first = client.get('/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer')
    assert first.status_code == 200 and '人工验收结论以项目阶段报告为准' in first.text and '人工验收尚未完成' not in first.text
    report['internalViewerHintAfterRestart'] = 'PASS'

pages = ['index.html','history.html','roles.html','facial.html','music.html','gallery.html','video.html','about.html']
report['unchangedFromSecondAcceptedHead'] = {}
for name in pages:
    baseline = subprocess.check_output(['git', 'show', '60bfc38:' + name], cwd=repo)
    report['unchangedFromSecondAcceptedHead'][name] = (repo / name).read_bytes() == baseline
assert all(report['unchangedFromSecondAcceptedHead'].values())
report['productDiffSinceSecondDelivery'] = subprocess.check_output(['git','diff','60bfc38','--name-only','--','backend/app','js','css','*.html'], cwd=repo).decode().splitlines()
assert report['productDiffSinceSecondDelivery'] == ['backend/app/assets/internal_viewer.py']
report['conclusion'] = 'PASS'
(out / 'local-get-and-continuity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print(json.dumps({'conclusion': report['conclusion'], 'localGetChecks': len(report['requests']), 'used': 2, 'remaining': 1, 'paidCalls': 0}))
