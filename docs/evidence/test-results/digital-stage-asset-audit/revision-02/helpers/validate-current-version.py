"""Free, read-only source/hash and documentation checks; no application imports.

Writes only this audit's final-validation.json. Does not convert, initialize,
register, execute model providers, or publish user assets.
"""
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path("D:/京剧/京剧")
EVIDENCE = ROOT / "docs/evidence/test-results/digital-stage-asset-audit/revision-02"


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    stage = json.loads((EVIDENCE.parent / 'stage-source-audit.json').read_text(encoding='utf-8'))
    characters = json.loads((EVIDENCE / 'character-glb-audit.json').read_text(encoding='utf-8'))
    sources = []
    for record in stage['files']:
        path = ROOT / stage['sourceDirectory'] / record['relative']
        sources.append({'file': path.relative_to(ROOT).as_posix(),
                        'hashUnchanged': digest(path) == record['sha256'],
                        'sizeUnchanged': path.stat().st_size == record['bytes']})
    for record in characters['reports']:
        path = ROOT / characters['sourceDirectory'] / record['filename']
        sources.append({'file': path.relative_to(ROOT).as_posix(),
                        'hashUnchanged': digest(path) == record['sha256'],
                        'sizeUnchanged': path.stat().st_size == record['sizeBytes']})

    originals = []
    for sha in ('bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a',
                '5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5'):
        path = ROOT.parent / '.runtime/xijing-ai/assets/models' / (sha + '.glb')
        originals.append({'sha256': sha, 'exists': path.is_file(),
                          'matchesPriorAcceptedHash': path.is_file() and digest(path) == sha})

    names = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, encoding='utf-8').splitlines()
    python = []
    for path in (EVIDENCE / 'helpers').glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'))
        python.append(path.name)

    markdown = [ROOT / 'docs' / name for name in (
        'reports/phase-05-requirements-evidence-map.md',
        'reports/phase-05-submission-checklist.md',
        'reports/phase-05-asset-provenance-and-permissions.md',
        'prompts/phase-05/README.md', 'reports/digital-stage-asset-audit.md',
        'prompts/digital-stage-assets/README.md',
        'evidence/test-results/digital-stage-asset-audit/README.md', 'evidence/test-results/digital-stage-asset-audit/revision-02/README.md')]
    links, external = [], 0
    for path in markdown:
        for target in re.findall(r'!?\[[^\]]*\]\(([^\n)]*)\)', path.read_text(encoding='utf-8-sig')):
            target = target.strip().strip('<>')
            if target.startswith(('http://', 'https://', 'mailto:', 'app://', 'plugin://')):
                external += 1
                continue
            target = unquote(target.split('#', 1)[0].split('?', 1)[0])
            if not target:
                continue
            resolved = Path(target) if re.match(r'^[A-Za-z]:[\\/]', target) else path.parent / target
            links.append({'file': path.relative_to(ROOT).as_posix(),
                          'target': target, 'exists': resolved.exists()})

    patterns = {
        'provider_credential': re.compile(r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}'),
        'github_credential': re.compile(r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}'),
        'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    }
    texts = set(markdown)
    texts.update(path for path in EVIDENCE.rglob('*') if path.is_file() and path.name != 'final-validation.json')
    texts.update((ROOT / 'docs/evidence/submission-requirements').glob('*.json'))
    findings, count = [], 0
    for path in sorted(texts):
        try:
            value = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            continue
        count += 1
        for kind, pattern in patterns.items():
            hits = len(pattern.findall(value))
            if hits:
                findings.append({'file': path.relative_to(ROOT).as_posix(), 'pattern': kind, 'count': hits})

    metadata = json.loads((ROOT / 'docs/evidence/submission-requirements/2026-10-29-source.json').read_text(encoding='utf-8'))
    screenshot_matches = digest(ROOT / metadata['savedFile']) == metadata['sha256']
    missing = [item for item in links if not item['exists']]
    body = {
        'atUtc': datetime.now(timezone.utc).isoformat(),
        'kind': 'FREE_READ_ONLY_ASSET_AND_DOCUMENT_VALIDATION',
        'command': '.venv/Scripts/python.exe -B ../.runtime/stage-asset-audit-20261029-revision2/validate-current-version.py',
        'sourceFiles': sources, 'sourceFileCount': len(sources), 'oldAcceptedGlbs': originals,
        'requirementScreenshotHashMatches': screenshot_matches,
        'trackedChangesOnlyDocs': all(name.startswith('docs/') for name in names),
        'pythonHelpersSyntaxCheckedNotExecuted': python, 'localMarkdownLinks': len(links),
        'externalLinksNotFetched': external, 'missingLinks': missing, 'links': links,
        'textFilesSecretScanned': count, 'secretFindings': findings,
        'scope': 'Source invariants and documentation only; not backend, paid API, final video/PDF or scene acceptance',
        'paidApiCalls': 0, 'neural4dCalls': 0, 'databaseAccess': False,
    }
    body['pass'] = (all(item['hashUnchanged'] and item['sizeUnchanged'] for item in sources)
                    and all(item['matchesPriorAcceptedHash'] for item in originals)
                    and screenshot_matches and body['trackedChangesOnlyDocs'] and not missing and not findings)
    (EVIDENCE / 'final-validation.json').write_text(json.dumps(body, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: body[key] for key in ('pass', 'sourceFileCount', 'localMarkdownLinks',
                                               'missingLinks', 'textFilesSecretScanned', 'secretFindings')}))
    return 0 if body['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
