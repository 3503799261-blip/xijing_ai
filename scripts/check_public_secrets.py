"""Scan public text files without printing any matched values. Exit nonzero to gate Git."""
import argparse
import json
from pathlib import Path
import re
import subprocess

PATTERNS = {
    'provider_credential': re.compile(r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}'),
    'github_credential': re.compile(r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}'),
    'private_key_header': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
}

def scan(root):
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root, check=True, capture_output=True)
    names = set(result.stdout.decode('utf-8').split('\0')) - {''}
    hits = []
    checked = 0
    for name in sorted(names):
        path = root / name
        if not path.is_file(): continue
        try: content = path.read_text(encoding='utf-8-sig')
        except (UnicodeError, OSError): continue
        checked += 1
        for label, pattern in PATTERNS.items():
            count = len(pattern.findall(content))
            if count: hits.append({'file': name, 'kind': label, 'count': count})
    return {'success': not hits, 'textFilesChecked': checked, 'findings': hits, 'scope': 'tracked and nonignored public UTF-8 files; no matched values logged'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = scan(Path(__file__).resolve().parents[1])
    if args.output: args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result['success'] else 1)
