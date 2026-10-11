"""Fetch pinned free viewer and licensed GLB fixture. No provider API or keys."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'js/vendor/model-viewer/model-viewer.min.js': 'https://cdn.jsdelivr.net/npm/@google/model-viewer@4.4.0/dist/model-viewer.min.js',
    'js/vendor/model-viewer/LICENSE': 'https://raw.githubusercontent.com/google/model-viewer/v4.4.0/LICENSE',
    'backend/tests/fixtures/phase4/Duck.glb': 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/Duck/glTF-Binary/Duck.glb',
    'backend/tests/fixtures/phase4/Duck-README.md': 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/Duck/README.md',
    'backend/tests/fixtures/phase4/SCEA-LICENSE.txt': 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/LICENSES/SCEA.txt',
}

if __name__ == '__main__':
    result = []
    for relative, url in FILES.items():
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(url, timeout=45) as response:
                data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError('Unexpected asset size')
            path.write_bytes(data)
        result.append({'path': relative, 'url': url, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    output = ROOT / 'backend/tests/fixtures/phase4/manifest.json'
    output.write_text(json.dumps({'modelViewerVersion': '4.4.0', 'fixturePurpose': 'Licensed existing test GLB; not Neural4D generated; no opera-cultural claim.', 'files': result}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
