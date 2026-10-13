"""Export the current session's PUBLIC Phase 4 evidence; never hidden reasoning."""
import argparse
import json
import re
from pathlib import Path
from export_phase_prompt import read_snapshot, public_text, export_public, source_path_redactions, stamp, digest


def redact(text):
    text = re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}', '[credential redacted]', text)
    text = re.sub(r'Bearer\s+(?!YOUR|<)[A-Za-z0-9._-]{16,}', 'Bearer [credential redacted]', text)
    # Official documentation also contains signed object-storage example URLs.
    # Remove the entire query-bearing resource URL, not just one token field,
    # including URLs embedded inside serialized tool output.
    text = re.sub(r'https?://cos\.(?:neural4d\.com|zmkj\.com)/[^\s"\\<>]+',
                  lambda match: '[signed model resource URL redacted]' if '?' in match[0] else match[0], text)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw, records, partial = read_snapshot(args.session_log)
    found = {}
    for line, record in records:
        payload = record.get('payload', {})
        if record.get('type') != 'response_item' or payload.get('type') != 'message' or payload.get('role') != 'user':
            continue
        for block in public_text(payload):
            text = block['text']
            if '执行 Phase 4 检查点A' in text and '你现在继续开发' in text:
                found.setdefault('00-original-user-request.txt', (line, text))
            if text.startswith('# 戏境 AI — Phase 4 检查点A最终修订'):
                found['01-final-architecture-revision.txt'] = (line, text)
            if text.startswith('Phase 4检查点A批准，开始正式开发。'):
                found['02-approved-development-request.txt'] = (line, text)
            if text.startswith('# 戏境 AI — Phase 4 双风格角色生成补充开发指令'):
                found['06-dual-style-user-request.txt'] = (line, text)
            if text.startswith('请按照以下顺序制定并执行Phase 4真实建模准备与调用流程：'):
                found['07-three-attempt-modeling-plan-request.txt'] = (line, text)
            if text.startswith('Phase 4 第一次Neural4D真实建模的Q版概念图已更新。'):
                found['08-bluewhite-concept-update-request.txt'] = (line, text)
            if text.lstrip().startswith('现在批准进行第1次 Neural4D 真实建模'):
                found['09-internal-technical-submission-approval.txt'] = (line, text)
            if ('已确认允许此次上传与衍生处理' in text and '已核实，此前为0次' in text
                    and text.startswith('<send_user_message_question_reply>')):
                found['10-internal-history-and-image-permission-reply.txt'] = (line, text)
            if '建模不带贴图消耗20个积分' in text and text.startswith('<send_user_message_question_reply>'):
                found['11-internal-account-credit-quote.txt'] = (line, text)
            if text.lstrip().startswith('# 戏境 AI — Phase 4 第一次真实模型恢复与验收指令'):
                found['12-first-model-recovery-request.txt'] = (line, text)
    if not {'00-original-user-request.txt', '01-final-architecture-revision.txt', '02-approved-development-request.txt'}.issubset(found):
        raise ValueError('Missing exact public Phase 4 user requests; do not invent evidence.')
    args.output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for filename, (_, text) in found.items():
        data = redact(text).encode('utf-8')
        (args.output / filename).write_bytes(data)
        hashes[filename] = digest(data)
    public, skipped = export_public(records, min(item[0] for item in found.values()), source_path_redactions(args.session_log))
    data = redact(''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in public)).encode('utf-8')
    (args.output / '03-public-conversation.jsonl').write_bytes(data)
    hashes['03-public-conversation.jsonl'] = digest(data)
    meta = {'exportedAt': stamp(), 'sourceSnapshotSha256': digest(raw), 'publicRecords': len(public), 'omittedPartialLine': partial, 'skipped': dict(skipped), 'files': hashes, 'scope': 'Actual public user messages, assistant commentary/final and matched tool evidence. No hidden reasoning, system/developer content or child internal messages. Snapshot; future records not included.'}
    (args.output / '04-export-metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'publicRecords': len(public), 'files': list(hashes)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
