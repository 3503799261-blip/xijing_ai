#!/usr/bin/env python3
"""Export public Phase 1 evidence from one explicitly supplied Codex JSONL log.

No log discovery, hidden reasoning, session metadata, or invented messages.
Requires Python 3.9+; uses only the standard library.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re

PROMPTS = (
    ("# 「戏境 AI」Phase 1", "00-original-user-request.md"),
    ("# 戏境 AI — Phase 1 检查点A已批准", "01-approved-development-request.md"),
)
PUBLIC_PHASES = {"commentary", "final", "final_answer"}
TOOL_CALLS = {"function_call", "custom_tool_call"}
TOOL_OUTPUTS = {"function_call_output", "custom_tool_call_output"}
PRIVATE_KEYS = {
    "encrypted_content", "reasoning", "summary", "session_meta", "turn_context",
    "reasoning_content", "internal_chat_message_metadata_passthrough", "metadata", "_meta",
}
MEDIA_TYPES = {"image", "image_url", "input_image", "audio", "input_audio", "video"}
DATA_URL = re.compile(r"data:(?:image|audio|video)/[^\s\"']+")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_text(payload: dict) -> list[dict]:
    return [
        {"type": block["type"], "text": block["text"]}
        for block in payload.get("content", [])
        if isinstance(block, dict)
        and block.get("type") in {"input_text", "output_text", "text"}
        and isinstance(block.get("text"), str)
    ]


def sanitize_tool_value(value, redactions=()):
    """Keep tool evidence, omit embedded media and internal metadata."""
    if isinstance(value, dict):
        if value.get("type") in {"reasoning", "session_meta", "turn_context"} or value.get("role") in {"system", "developer"}:
            return {"omitted": "private nested record"}
        if value.get("type") in MEDIA_TYPES:
            return {"type": value["type"], "omitted": "embedded media; see screenshot evidence"}
        return {
            key: sanitize_tool_value(item, redactions)
            for key, item in value.items()
            if key not in PRIVATE_KEYS and not key.startswith("internal_")
        }
    if isinstance(value, list):
        return [sanitize_tool_value(item, redactions) for item in value]
    if isinstance(value, str):
        result = DATA_URL.sub("[embedded media data omitted]", value)
        for original, replacement in redactions:
            result = result.replace(original, replacement)
        # Tool outputs sometimes wrap JSON in a text block. Filter nested private
        # fields there too; retain the original formatting when nothing changes.
        if result.lstrip().startswith(("{", "[")):
            try:
                decoded = json.loads(result)
            except json.JSONDecodeError:
                pass
            else:
                filtered = sanitize_tool_value(decoded, redactions)
                if filtered != decoded:
                    return json.dumps(filtered, ensure_ascii=False)
        return result
    return value


def read_snapshot(path: Path):
    data = path.read_bytes()
    records = []
    omitted_partial_line = False
    lines = data.splitlines()
    for index, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # A running log may have a final line that has not finished writing.
            if index == len(lines) and not data.endswith(b"\n"):
                omitted_partial_line = True
                break
            raise ValueError(f"Invalid JSON at source line {index}")
        if not isinstance(record, dict):
            raise ValueError(f"Non-object record at source line {index}")
        records.append((index, record))
    return data, records, omitted_partial_line


def find_prompts(records):
    found = {}
    for line, record in records:
        payload = record.get("payload", {})
        if record.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        if payload.get("type") != "message" or payload.get("role") != "user":
            continue
        for block in public_text(payload):
            text = block["text"]
            for prefix, filename in PROMPTS:
                if text.startswith(prefix):
                    if filename in found:
                        raise ValueError(f"Ambiguous duplicate prompt: {filename}")
                    found[filename] = (line, record.get("timestamp"), text)
    missing = [filename for _, filename in PROMPTS if filename not in found]
    if missing:
        raise ValueError("Missing exact Phase 1 user prompt(s): " + ", ".join(missing))
    return found


def export_public(records, start_line, redactions=()):
    exported = []
    calls = set()
    skipped = Counter()
    for line, record in records:
        if line < start_line:
            continue
        payload = record.get("payload", {})
        if record.get("type") != "response_item" or not isinstance(payload, dict):
            skipped[record.get("type", "unknown")] += 1
            continue
        kind = payload.get("type")
        base = {"source_line": line, "source_timestamp": record.get("timestamp")}
        if kind == "message":
            role = payload.get("role")
            phase = payload.get("phase", payload.get("channel"))
            if role not in {"user", "assistant"}:
                skipped["private_message"] += 1
                continue
            if role == "assistant" and phase not in PUBLIC_PHASES:
                skipped["non_public_assistant"] += 1
                continue
            content = public_text(payload)
            if not content:
                skipped["non_text_message"] += 1
                continue
            item = {**base, "type": "message", "role": role, "content": content}
            if role == "assistant":
                item["phase"] = phase
            exported.append(item)
        elif kind in TOOL_CALLS:
            item = {**base, "type": kind}
            for key in ("name", "namespace", "call_id", "arguments", "input", "status"):
                if key in payload:
                    item[key] = sanitize_tool_value(payload[key], redactions)
            if payload.get("call_id"):
                calls.add(payload["call_id"])
            exported.append(item)
        elif kind in TOOL_OUTPUTS:
            if payload.get("call_id") not in calls:
                skipped["unmatched_tool_output"] += 1
                continue
            exported.append({
                **base, "type": kind, "call_id": payload["call_id"],
                "output": sanitize_tool_value(payload.get("output"), redactions),
            })
        else:
            # Includes reasoning and child-agent communications.
            skipped[kind or "unknown_response_item"] += 1
    return exported, skipped


def write_bytes(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    if path.read_bytes() != data:
        raise RuntimeError(f"Exact byte verification failed: {path.name}")
    return digest(path.read_bytes())


def source_path_redactions(source: Path):
    """Hide the local session-log identity even when a tool command names it."""
    variants = {str(source), str(source).replace("\\", "/"), source.name}
    variants.update(value.replace("\\", "\\\\") for value in tuple(variants))
    redactions = [(value, "<current-session-log>") for value in variants]
    identities = re.findall(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        source.name,
    )
    redactions.extend((value, "<private-session-id>") for value in identities)
    return tuple(sorted(redactions, key=lambda item: len(item[0]), reverse=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-log", type=Path, required=True,
                        help="Exact current-session JSONL path; no directory scanning")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Reading the explicit path needs no directory traversal or realpath query.
    # Some managed Windows environments permit read_bytes but deny realpath.
    source = args.session_log
    if not source.is_absolute() or source.suffix.lower() != ".jsonl":
        parser.error("--session-log must name one absolute .jsonl file path")
    output = args.output.resolve()
    if source == output or source.parent == output:
        parser.error("Output must be separate from the source session-log directory")
    started_at = stamp()
    raw, records, partial_line = read_snapshot(source)
    prompts = find_prompts(records)
    first_line = prompts[PROMPTS[0][1]][0]
    exported, skipped = export_public(records, first_line, source_path_redactions(source))
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    for _, filename in PROMPTS:
        line, timestamp, text = prompts[filename]
        source_bytes = text.encode("utf-8")
        output_sha = write_bytes(output / filename, source_bytes)
        checks.append({
            "file": filename, "source_line": line, "source_timestamp": timestamp,
            "characters": len(text), "bytes_utf8": len(source_bytes),
            "source_text_sha256": digest(source_bytes),
            "export_file_sha256": output_sha,
            "exact_utf8_byte_match": (output / filename).read_bytes() == source_bytes,
            "text_rule": "Exact single input_text block; no added heading or newline",
        })
    conversation = b"".join(
        (json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for item in exported
    )
    conversation_sha = write_bytes(output / "02-public-conversation-snapshot.jsonl", conversation)
    metadata = {
        "schema_version": 1,
        "scope": "Current explicitly supplied session only, from first Phase 1 user prompt to read snapshot",
        "source": {
            "selection": "One exact --session-log argument; no discovery or other log reads",
            "snapshot_sha256": digest(raw), "snapshot_bytes": len(raw),
            "parsed_records": len(records), "first_phase1_source_line": first_line,
            "last_complete_source_line": records[-1][0] if records else None,
            "incomplete_final_line_omitted": partial_line,
        },
        "export": {
            "started_at_utc": started_at, "completed_at_utc": stamp(),
            "timezone_for_user_facing_dates": "Asia/Shanghai",
            "local_date": datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
            "records": len(exported),
            "counts": dict(Counter(item["type"] for item in exported)),
            "first_source_timestamp": exported[0].get("source_timestamp") if exported else None,
            "last_source_timestamp": exported[-1].get("source_timestamp") if exported else None,
            "conversation_sha256": conversation_sha,
        },
        "prompt_checks": checks,
        "excluded": [
            "system/developer messages", "reasoning/encrypted content",
            "session/turn metadata and identities", "usage/world-state events",
            "child-agent messages", "embedded media data",
        ],
        "skipped_record_counts": dict(skipped),
        "limitations": [
            "Point-in-time snapshot, not an automatic completion transcript.",
            "Source absolute path and session identity are omitted from metadata and redacted in tool text.",
            "Only direct response_item records are exported; event_msg duplicates are omitted.",
            "Tool text preserves actual operations; screenshot files are separate evidence.",
            "A later invocation refreshes the snapshot with only events that really occurred.",
        ],
    }
    write_bytes(output / "03-export-metadata.json",
                (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({
        "exported_records": len(exported),
        "prompt_exact_matches": all(item["exact_utf8_byte_match"] for item in checks),
        "prompt_characters": [item["characters"] for item in checks],
        "conversation_sha256": conversation_sha,
        "snapshot_time_utc": metadata["export"]["completed_at_utc"],
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
