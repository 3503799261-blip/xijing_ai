"""Capture real chat responses once per question, or prepare an offline review.

Chat mode may spend the backend's approved LLM budget. It performs no retries.
Offline --review-existing mode performs no HTTP, embedding, or LLM requests.
Candidate labels and fact-review templates are not human correctness scores.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from statistics import mean
import time
from typing import Any
from urllib.parse import quote, urlsplit
import uuid

import httpx

from backend.app.config import PROJECT_ROOT, Settings

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
ANNOTATION = "assistant_source_checked_candidate"
CITATION_FIELDS = ("id", "title", "sourceId", "locator", "url", "excerpt", "contentKind")


def timestamp() -> str:
    return datetime.now(TZ).isoformat()


def public_text(value: str) -> tuple[str, bool]:
    cleaned = re.sub(r"(?i)\b(?:sk-|bearer\s+)[a-z0-9_-]{16,}", "[REDACTED_CREDENTIAL_PATTERN]", value)
    return cleaned, cleaned != value


def safe_response(data: Any) -> tuple[dict, bool, bool]:
    """Only archive public contract fields; never arbitrary error bodies or HTML."""
    if not isinstance(data, dict):
        return {}, False, False
    redacted = False
    if isinstance(data.get("error"), dict):
        error = data["error"]
        message, redacted = public_text(str(error.get("message", "服务返回错误。")))
        return {"error": {"code": str(error.get("code", "HTTP_ERROR")), "message": message, "retryable": bool(error.get("retryable", False))}, "requestId": data.get("requestId")}, False, redacted
    if not (isinstance(data.get("answer"), str) and data["answer"].strip()
            and isinstance(data.get("citations"), list) and len(data["citations"]) <= 5
            and isinstance(data.get("uncertain"), bool) and isinstance(data.get("requestId"), str)):
        return {}, False, False
    answer, redacted = public_text(data["answer"])
    citations = []
    for citation in data["citations"]:
        if not isinstance(citation, dict) or any(not isinstance(citation.get(key), str) for key in CITATION_FIELDS if key != "url"):
            return {}, False, redacted
        if citation.get("url") is not None and not isinstance(citation["url"], str):
            return {}, False, redacted
        item = {}
        for key in CITATION_FIELDS:
            value = citation.get(key)
            if isinstance(value, str):
                value, changed = public_text(value)
                redacted = redacted or changed
            item[key] = value
        citations.append(item)
    return {"answer": answer, "citations": citations, "uncertain": data["uncertain"], "requestId": data["requestId"]}, True, redacted


def load_questions(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Questions must be a nonempty list.")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in seen:
            raise ValueError("Question IDs must be unique strings.")
        seen.add(row["id"])
        if not isinstance(row.get("question"), str) or not row["question"].strip() or len(row["question"].encode("utf-16-le")) // 2 > 600:
            raise ValueError("Question does not meet the API length constraint.")
        if row.get("annotation_status") != ANNOTATION or not isinstance(row.get("expect_insufficient"), bool):
            raise ValueError("Unsupported annotation scope.")
        for key in ("expected_facts", "expected_source_ids", "expected_section_ids"):
            if not isinstance(row.get(key), list) or not all(isinstance(value, str) for value in row[key]):
                raise ValueError("Invalid candidate annotation lists.")
    return rows, sha256(raw).hexdigest()


def save(path: Path, report: dict) -> None:
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def index_snapshot() -> tuple[Path, dict]:
    data_dir = Settings().rag_data_dir
    manifest = json.loads((data_dir / "active.json").read_text(encoding="utf-8"))
    generation = manifest["generation_id"]
    if not isinstance(generation, str) or not re.fullmatch(r"gen-[A-Za-z0-9_-]+", generation):
        raise ValueError("Invalid index generation ID.")
    db = (data_dir / "generations" / generation / "knowledge.sqlite3").resolve()
    if data_dir.resolve() not in db.parents or not db.is_file():
        raise ValueError("Canonical database is unavailable.")
    return db, {key: manifest.get(key) for key in ("generation_id", "corpus_hash", "documents", "chunks", "model_id", "model_revision", "dimension", "review_scope")}


def chat_summary(records: list[dict], total: int) -> dict:
    successful = [row for row in records if row["status"] == "response_received"]
    return {
        "requestedQuestionCount": total, "attemptedQuestionCount": len(records),
        "responseReceivedCount": len(successful), "failedCount": len(records) - len(successful),
        "apiResponseSuccessRate": len(successful) / len(records) if records else None,
        "meanSuccessfulHttpSeconds": mean(row["elapsedSeconds"] for row in successful) if successful else None,
        "candidateUncertaintyFlagAgreement": mean(row["response"]["uncertain"] == row["expectInsufficient"] for row in successful) if successful else None,
        "failedQuestionIds": [row["id"] for row in records if row["status"] != "response_received"],
        "uncertaintyFlagDisagreements": [row["id"] for row in successful if row["response"]["uncertain"] != row["expectInsufficient"]],
        "humanAnswerCorrectnessRate": None,
        "scope": "HTTP success and candidate uncertainty flags only; no human semantic scoring or per-response LLM usage is inferred.",
    }


def capture(args, rows: list[dict], question_hash: str, path: Path) -> dict:
    base = args.base_url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Chat evaluation only accepts a credential-free local HTTP origin.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid local HTTP port.")
    selected = rows[:args.limit] if args.limit is not None else rows
    run_id = uuid.uuid4().hex
    _, manifest = index_snapshot()
    report = {"status": "running", "metadata": {
        "label": args.label, "runId": run_id, "startedAt": timestamp(), "baseUrl": base,
        "questionSetFile": args.questions.name, "questionSetSHA256": question_hash,
        "scriptSHA256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "annotationScope": ANNOTATION, "humanGoldLabels": False,
        "automaticRetries": 0, "sequentialRequests": True, "httpTimeoutSeconds": args.timeout,
        "index": manifest, "llmUsageMeasuredByThisScript": False,
        "usageNote": "The endpoint may answer insufficient-evidence cases without an LLM call. Actual model usage/cost must be checked against the backend ledger separately.",
        "logPolicy": "Console contains question IDs, status, HTTP status and request IDs only; arbitrary bodies, credentials and exception strings are omitted.",
    }, "records": []}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Reserve output before paid requests; never silently overwrite a previous run.
    with path.open("x", encoding="utf-8") as target:
        target.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    try:
        with httpx.Client(timeout=args.timeout, follow_redirects=False, trust_env=False, transport=httpx.HTTPTransport(retries=0)) as client:
            for index, question in enumerate(selected, start=1):
                key = "eval-" + run_id + "-" + str(index) + "-" + sha256(question["id"].encode()).hexdigest()[:12]
                record = {"id": question["id"], "question": question["question"],
                          "annotationStatus": question["annotation_status"], "expectInsufficient": question["expect_insufficient"],
                          "idempotencyKey": key, "attempts": 1, "status": "request_pending", "startedAt": timestamp()}
                report["records"].append(record)
                save(path, report)
                started = time.perf_counter()
                try:
                    response = client.post(base + "/api/v1/chat", headers={"X-Idempotency-Key": key}, json={"question": question["question"]})
                    record.update({"httpStatus": response.status_code, "headerRequestId": response.headers.get("x-request-id"), "rawResponseSHA256": sha256(response.content).hexdigest()})
                    try:
                        public, valid, redacted = safe_response(response.json())
                    except ValueError:
                        public, valid, redacted = {}, False, False
                    record.update({"response": public, "responseSchemaValid": valid, "redactionApplied": redacted,
                                   "requestId": public.get("requestId"),
                                   "status": "response_received" if response.status_code == 200 and valid else "api_error"})
                except httpx.RequestError as exc:
                    record.update({"status": "network_error", "errorType": type(exc).__name__, "requestId": None})
                record.update({"elapsedSeconds": round(time.perf_counter() - started, 6), "finishedAt": timestamp()})
                report["summary"] = chat_summary(report["records"], len(selected))
                save(path, report)
                print(json.dumps({key: record.get(key) for key in ("id", "status", "httpStatus", "requestId")}, ensure_ascii=True), flush=True)
        report["status"] = "completed" if not report["summary"]["failedCount"] else "completed_with_failures"
    except KeyboardInterrupt:
        report["status"] = "interrupted"
        if report["records"] and report["records"][-1]["status"] == "request_pending":
            report["records"][-1]["status"] = "interrupted_unknown_server_result"
    except Exception as exc:
        report["status"] = "failed"
        report["errorType"] = type(exc).__name__
        raise
    finally:
        report["metadata"]["finishedAt"] = timestamp()
        report["summary"] = chat_summary(report["records"], len(selected))
        save(path, report)
    return report


def normalized(text: str) -> str:
    return "".join(text.split())


def offline_review(args, questions: list[dict], question_hash: str, path: Path) -> dict:
    original_bytes = args.review_existing.read_bytes()
    original = json.loads(original_bytes.decode("utf-8"))
    records = original.get("records")
    if not isinstance(records, list):
        raise ValueError("Existing answer archive has no records list.")
    candidates = {row["id"]: row for row in questions}
    db, manifest = index_snapshot() if args.database is None else (args.database.resolve(), {})
    if not db.is_file():
        raise ValueError("Canonical database is unavailable.")
    documents, sections = {}, {}
    document_hashes = {}
    for document_path in sorted(args.documents.glob("*.json")):
        raw = document_path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
        source = document["source"]
        sid = source["source_id"]
        if sid in documents:
            raise ValueError("Duplicate source ID in original documents.")
        documents[sid] = source
        document_hashes[document_path.name] = sha256(raw).hexdigest()
        for section in document["sections"]:
            sections[(sid, section["section_id"])] = section
    result = {"status": "review_template_prepared", "metadata": {
        "label": args.label, "preparedAt": timestamp(), "originalArchiveFile": args.review_existing.name,
        "originalArchiveSHA256": sha256(original_bytes).hexdigest(), "questionSetSHA256": question_hash,
        "originalDocumentSHA256": document_hashes, "index": manifest,
        "sqliteMode": "read-only; no Qdrant, embedding, HTTP or LLM operation",
        "humanGoldLabels": False, "annotationScope": ANNOTATION,
        "scope": "Citation identity/provenance checks are structural. Fact support, omissions and answer correctness remain explicit review tasks; no human accuracy is claimed.",
    }, "cases": []}
    connection = sqlite3.connect("file:" + quote(db.as_posix(), safe="/:") + "?mode=ro", uri=True)
    try:
        for record in (records[:args.limit] if args.limit is not None else records):
            candidate = candidates.get(record.get("id"))
            if candidate is None or record.get("question") != candidate["question"]:
                raise ValueError("Existing archive does not match the candidate questions.")
            response = record.get("response", {})
            citation_checks = []
            for citation in response.get("citations", []):
                found = connection.execute("SELECT c.data_json,s.data_json FROM chunks c JOIN sources s USING(source_id) WHERE chunk_id=?", (citation.get("id"),)).fetchone()
                check = {"citationId": citation.get("id"), "canonicalChunkFound": bool(found), "canonicalFieldsMatch": False, "originalSourceMetadataMatches": False, "originalSectionContainsExcerpt": False}
                if found:
                    chunk, source = map(json.loads, found)
                    expected = {"id": chunk["chunk_id"], "sourceId": chunk["source_id"], "title": source["title"], "locator": chunk["locator"], "url": source["source_url"], "excerpt": chunk["content"], "contentKind": source["content_kind"]}
                    check["canonicalFieldsMatch"] = all(citation.get(key) == value for key, value in expected.items())
                    check["mismatchedFields"] = [key for key, value in expected.items() if citation.get(key) != value]
                    raw_source = documents.get(source["source_id"])
                    original_section = sections.get((chunk["source_id"], chunk["section_id"]))
                    check["sectionId"] = chunk["section_id"]
                    check["sourceId"] = source["source_id"]
                    check["canonicalExcerpt"] = chunk["content"]
                    check["originalSourceMetadataMatches"] = bool(raw_source and all(raw_source.get(key) == source.get(key) for key in ("source_id", "title", "source_url", "document_version", "review_status", "content_kind")))
                    check["originalSectionContainsExcerpt"] = bool(original_section and normalized(chunk["content"]) in normalized(original_section["content"]))
                check["structuralProvenanceValid"] = all(check[key] for key in ("canonicalChunkFound", "canonicalFieldsMatch", "originalSourceMetadataMatches", "originalSectionContainsExcerpt"))
                check["claimActuallySupported"] = "not_reviewed"
                citation_checks.append(check)
            used_sections = {check.get("sectionId") for check in citation_checks if check["canonicalFieldsMatch"]}
            result["cases"].append({
                "id": candidate["id"], "question": candidate["question"], "requestId": record.get("requestId"),
                "captureStatus": record.get("status"), "answer": response.get("answer"), "uncertain": response.get("uncertain"),
                "expectInsufficient": candidate["expect_insufficient"],
                "candidateUncertaintyFlagAgreement": response.get("uncertain") == candidate["expect_insufficient"] if record.get("status") == "response_received" else None,
                "citations": response.get("citations", []), "citationChecks": citation_checks,
                "expectedSectionIds": candidate["expected_section_ids"], "citedExpectedSectionIds": sorted(used_sections & set(candidate["expected_section_ids"])),
                "expectedFactReviewTemplate": [{"expectedFact": fact, "assistantAssessment": "not_reviewed", "supportingCitationIds": [], "reason": None, "humanAssessment": "pending"} for fact in candidate["expected_facts"]],
                "assistantReview": {"status": "not_reviewed", "unsupportedAssertions": None, "missingExpectedFacts": None, "sourceSupportNotes": None, "reviewer": None, "reviewedAt": None},
                "humanReview": {"status": "pending", "answerCorrect": None, "reviewer": None, "reviewedAt": None},
            })
    finally:
        connection.close()
    checks = [check for row in result["cases"] for check in row["citationChecks"]]
    result["summary"] = {"capturedCaseCount": len(result["cases"]), "citationCount": len(checks),
                         "canonicalCitationMappingRate": mean(check["canonicalFieldsMatch"] for check in checks) if checks else None,
                         "structuralSourceTraceabilityRate": mean(check["structuralProvenanceValid"] for check in checks) if checks else None,
                         "failedStructuralCitationIds": [check["citationId"] for check in checks if not check["structuralProvenanceValid"]],
                         "assistantSemanticReviewsCompleted": 0, "humanReviewsCompleted": 0, "humanAnswerCorrectnessRate": None}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        target.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--label", default=datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f"))
    parser.add_argument("--questions", type=Path, default=PROJECT_ROOT / "knowledge/evaluation/questions.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--review-existing", type=Path, help="Offline citation checks and review template; no paid requests.")
    parser.add_argument("--database", type=Path, help="Optional original SQLite generation for offline review.")
    parser.add_argument("--documents", type=Path, default=PROJECT_ROOT / "knowledge/documents")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.label):
        parser.error("--label must contain at most 80 alphanumeric/hyphen/underscore characters.")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive.")
    if not 1 <= args.timeout <= 120:
        parser.error("--timeout must be between 1 and 120 seconds.")
    if args.database is not None and args.review_existing is None:
        parser.error("--database is only used with --review-existing.")
    path = args.output or PROJECT_ROOT / "docs/evidence/test-results" / f"phase-02-answers-{args.label}{'-review' if args.review_existing else ''}.json"
    if path.exists():
        parser.error("Output already exists; use another label/path. No requests were sent.")
    try:
        rows, digest = load_questions(args.questions)
        result = offline_review(args, rows, digest, path) if args.review_existing else capture(args, rows, digest, path)
        print(json.dumps({"status": result["status"], "summary": result.get("summary")}, ensure_ascii=True), flush=True)
        return 0 if result["status"] in {"completed", "review_template_prepared"} else 1
    except Exception as exc:
        # Never print provider exceptions, environment values, local paths or bodies.
        print(json.dumps({"status": "failed", "errorType": type(exc).__name__, "message": "Evaluation did not finish; inspect saved records if present. No automatic retry was performed."}, ensure_ascii=True), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
