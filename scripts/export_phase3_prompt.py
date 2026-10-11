"""Export public Phase 3 messages/tools from one explicit current log only."""
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
    candidates = []
    for line, record in records:
        payload = record.get('payload', {})
        if record.get('type') != 'response_item' or not isinstance(payload, dict) or payload.get('type') != 'message' or payload.get('role') != 'user':
            continue
        if any('fee37e08-c9f0-4909-a497-c17298bd6f8c' in block['text'] for block in original.public_text(payload)):
            candidates.append(line)
    if len(candidates) != 1:
        raise ValueError('Expected one explicit Phase 3 attachment request')
    public, skipped = original.export_public(records, candidates[0], original.source_path_redactions(args.session_log))
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
    data = b''.join((json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8') for item in public)
    digest = original.write_bytes(args.output/'02-public-conversation.jsonl', data)
    metadata = {
        'schemaVersion': '1.0', 'scope': 'Real public Phase 3 request, architecture, approval and development snapshot',
        'exportedAt': datetime.now(timezone.utc).isoformat(),
        'sourceSnapshotSha256': hashlib.sha256(raw).hexdigest(),
        'firstSourceLine': candidates[0], 'lastCompleteSourceLine': records[-1][0],
        'partialFinalLineOmitted': partial, 'records': len(public),
        'counts': dict(Counter(r['type'] for r in public)), 'conversationSha256': digest,
        'originalRequestSha256': hashlib.sha256((args.output/'00-original-user-request.txt').read_bytes()).hexdigest(),
        'redactions': dict(redacted), 'skipped': skipped,
        'excluded': ['hidden reasoning','system/developer messages','credential values','embedded media','private child-agent records'],
        'limitations': ['Only one explicit current session was read.', 'Point-in-time snapshot; future replies are not invented.']
    }
    original.write_bytes(args.output/'03-export-metadata.json', (json.dumps(metadata,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'records':len(public),'redactedCredentials':redacted['credential_occurrences']},ensure_ascii=True))

if __name__=='__main__': main()
