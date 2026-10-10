"""Export only public Phase 2 evidence from one explicit log, with secret redaction."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
PATTERNS = (
    re.compile(r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}'),
    re.compile(r'(?i)(Bearer\s+)[A-Za-z0-9._-]{20,}'),
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('public_export', Path(__file__).with_name('export_phase_prompt.py'))
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    raw, records, partial = original.read_snapshot(args.session_log)
    prompts = {}
    for line, record in records:
        payload = record.get('payload', {})
        if record.get('type') != 'response_item' or not isinstance(payload, dict) or payload.get('type') != 'message' or payload.get('role') != 'user':
            continue
        for block in original.public_text(payload):
            text = block['text']
            name = None
            if text.startswith('# 「戏境 AI」Phase 2'):
                name = '00-original-user-request.md'
            if text.startswith('下面是为你的「戏境 AI」项目重新整合的 Phase 2'):
                name = '03-approved-development-v3.md'
            if name:
                if name in prompts: raise ValueError('Duplicate original prompt')
                if any(pattern.search(text) for pattern in PATTERNS):
                    raise ValueError('A selected original prompt contains a credential; exact export refused')
                prompts[name] = (line, record.get('timestamp'), text)
    if len(prompts) != 2: raise ValueError('Expected original architecture and approved V3 prompts')
    first = prompts['00-original-user-request.md'][0]
    public, skipped = original.export_public(records, first, original.source_path_redactions(args.session_log))
    redacted = Counter()
    def scrub(value):
        if isinstance(value, str):
            for pattern in PATTERNS:
                value, count = pattern.subn('<credential-redacted>', value)
                redacted['credential_occurrences'] += count
            return value
        if isinstance(value, dict): return {k: scrub(v) for k, v in value.items()}
        if isinstance(value, list): return [scrub(v) for v in value]
        return value
    public = scrub(public)
    args.output.mkdir(parents=True, exist_ok=True)
    checks = []
    for name, (line, timestamp, text) in prompts.items():
        data = text.encode('utf-8')
        sha = original.write_bytes(args.output / name, data)
        checks.append({'file': name, 'source_line': line, 'source_timestamp': timestamp, 'characters': len(text), 'sha256': sha, 'exact_utf8_byte_match': (args.output / name).read_bytes() == data})
    conversation = b''.join((json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8') for item in public)
    conversation_sha = original.write_bytes(args.output / '01-checkpoint-a-public-conversation.jsonl', conversation)
    metadata = {'schema_version': 2, 'scope': 'Actual public Phase 2 architecture and approved development, point-in-time snapshot', 'source': {'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'parsed_records': len(records), 'first_source_line': first, 'last_complete_source_line': records[-1][0], 'partial_final_line_omitted': partial, 'selection': 'One explicit current log; no other sessions scanned'}, 'export': {'completed_at_utc': datetime.now(timezone.utc).isoformat(), 'records': len(public), 'counts': dict(Counter(r['type'] for r in public)), 'conversation_sha256': conversation_sha}, 'prompt_checks': checks, 'redactions': dict(redacted), 'excluded': ['hidden reasoning', 'system/developer', 'session identity', 'embedded media', 'private child-agent records', 'credential values'], 'limitations': ['Snapshot contains only events already recorded; no future tests or replies are invented.', 'Credential disclosure is retained only as redacted public evidence; exposed value is never copied into project files.']}
    original.write_bytes(args.output / '02-export-metadata.json', (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'records': len(public), 'prompt_exact_matches': all(c['exact_utf8_byte_match'] for c in checks), 'redacted_credentials': redacted['credential_occurrences']}, ensure_ascii=True))

if __name__ == '__main__': main()
