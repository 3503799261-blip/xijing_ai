"""Evaluate real local retrieval against assistant-checked evidence candidates.

This script never invokes an LLM provider. These annotations are candidates,
not human gold labels, so the output deliberately does not call them Recall@5.
Run from the project root with ``python -m backend.scripts.evaluate_retrieval``.
Stop the application first: Qdrant local and the canonical SQLite store have
one owner, and opening, searching, and closing here stay on the same thread.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import re
from statistics import mean
import time
from typing import Any

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.services.runtime import Runtime


ANNOTATION_STATUS = "assistant_source_checked_candidate"
MODES = ("vector", "hybrid")
LOCAL_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def load_questions(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Question set must be a nonempty JSON list.")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid question record.")
        qid = row.get("id")
        if not isinstance(qid, str) or not qid or qid in seen:
            raise ValueError("Question IDs must be nonempty and unique.")
        seen.add(qid)
        if not isinstance(row.get("question"), str) or not row["question"].strip():
            raise ValueError("Question text must not be empty.")
        if row.get("annotation_status") != ANNOTATION_STATUS:
            raise ValueError("This evaluator only accepts the documented candidate annotation scope.")
        if not isinstance(row.get("expect_insufficient"), bool):
            raise ValueError("expect_insufficient must be a boolean.")
        for key in ("expected_facts", "expected_source_ids", "expected_section_ids"):
            if not isinstance(row.get(key), list) or not all(isinstance(x, str) and x for x in row[key]):
                raise ValueError("Question annotation lists are invalid.")
        if row["expect_insufficient"]:
            if row["expected_source_ids"] or row["expected_section_ids"]:
                raise ValueError("Insufficient-evidence questions must not invent an evidence target.")
        elif not row["expected_section_ids"] or not row["expected_source_ids"]:
            raise ValueError("Supported questions require real candidate section and source IDs.")
    return rows, sha256(raw).hexdigest()


def evidence_integrity(runtime: Runtime, evidence: dict[str, Any]) -> bool:
    """Check citations against canonical stored text, not just ID formatting."""
    try:
        chunk_id = evidence["id"]
        chunk = runtime.store.chunk(chunk_id)
        source = chunk["source"]
        return bool(
            chunk_id == evidence["chunkId"] == chunk["chunk_id"]
            and evidence["sourceId"] == chunk["source_id"] == source["source_id"]
            and evidence["sectionId"] == chunk["section_id"]
            and evidence["excerpt"] == chunk["content"]
            and evidence["title"] == source["title"]
            and evidence["url"] == source["source_url"]
            and evidence["locator"] == chunk["locator"]
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_case(runtime: Runtime, row: dict[str, Any], mode: str, top_k: int) -> dict[str, Any]:
    started = time.perf_counter()
    expected_sections = set(row["expected_section_ids"])
    expected_sources = set(row["expected_source_ids"])
    base = {
        "id": row["id"],
        "category": row.get("category"),
        "question": row["question"],
        "annotationStatus": row["annotation_status"],
        "evaluationScope": row.get("evaluation_scope", "assistant candidate questions; human review pending"),
        "expectedFacts": row["expected_facts"],
        "expectedSectionIds": row["expected_section_ids"],
        "expectedSourceIds": row["expected_source_ids"],
        "expectInsufficient": row["expect_insufficient"],
    }
    try:
        result = runtime.search_service.search(row["question"], top_k=top_k, mode=mode)
        evidence = result["evidence"]
        returned_sections = {hit["sectionId"] for hit in evidence}
        returned_sources = {hit["sourceId"] for hit in evidence}
        matched_sections = expected_sections & returned_sections
        matched_sources = expected_sources & returned_sources
        checks = [evidence_integrity(runtime, hit) for hit in evidence]
        accepted_ids = {hit["id"] for hit in evidence}
        candidate_contexts = []
        for rank, candidate in enumerate(result["candidateScores"], start=1):
            chunk = runtime.store.chunk(candidate["chunkId"])
            candidate_contexts.append({
                "chunkId": candidate["chunkId"],
                "vectorRank": rank,
                "vectorScore": candidate["score"],
                "sourceId": chunk["source_id"],
                "sectionId": chunk["section_id"],
                "acceptedAsEvidence": candidate["chunkId"] in accepted_ids,
                "matchesCandidateSection": chunk["section_id"] in expected_sections,
            })
        predicted_insufficient = bool(result["uncertain"])
        return {
            **base,
            "status": "completed",
            "retrievalMode": mode,
            "threshold": result["threshold"],
            "uncertain": predicted_insufficient,
            "insufficiencyPredictionMatchesCandidate": predicted_insufficient == row["expect_insufficient"],
            "returnedSectionIds": sorted(returned_sections),
            "returnedSourceIds": sorted(returned_sources),
            "matchedExpectedSectionIds": sorted(matched_sections),
            "matchedExpectedSourceIds": sorted(matched_sources),
            "missingExpectedSectionIds": sorted(expected_sections - returned_sections),
            "candidateEvidenceCoverageAt5": len(matched_sections) / len(expected_sections) if expected_sections else None,
            "candidateSourceCoverageAt5": len(matched_sources) / len(expected_sources) if expected_sources else None,
            "evidenceCount": len(evidence),
            "canonicalEvidenceChecks": checks,
            "canonicalEvidenceIntegrity": all(checks),
            "evidence": evidence,
            "candidateScores": result["candidateScores"],
            "canonicalCandidateScoreContexts": candidate_contexts,
            "elapsedSeconds": result["elapsedSeconds"],
            "wallElapsedSeconds": round(time.perf_counter() - started, 6),
        }
    except Exception as exc:
        # Do not serialize exception strings, paths, settings, or provider keys.
        return {
            **base,
            "status": "failed",
            "retrievalMode": mode,
            "errorType": type(exc).__name__,
            "errorCode": getattr(exc, "code", "RETRIEVAL_EVALUATION_ERROR"),
            "wallElapsedSeconds": round(time.perf_counter() - started, 6),
        }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in cases if row["status"] == "completed"]
    supported = [row for row in completed if not row["expectInsufficient"]]
    insufficient = [row for row in completed if row["expectInsufficient"]]
    expected_count = sum(len(row["expectedSectionIds"]) for row in supported)
    matched_count = sum(len(row["matchedExpectedSectionIds"]) for row in supported)
    evidence_checks = [check for row in completed for check in row["canonicalEvidenceChecks"]]
    false_rejections = [row["id"] for row in supported if row["uncertain"]]
    false_acceptances = [row["id"] for row in insufficient if not row["uncertain"]]
    missing = [row["id"] for row in supported if row["missingExpectedSectionIds"]]
    timing = [row["elapsedSeconds"] for row in completed]
    return {
        "metricScope": "Assistant source-checked candidate annotations; not human gold Recall@5 or answer correctness.",
        "questionCount": len(cases),
        "completedCount": len(completed),
        "failedCount": len(cases) - len(completed),
        "supportedCandidateCount": len(supported),
        "insufficientCandidateCount": len(insufficient),
        "candidateEvidenceCoverageAt5Macro": mean(row["candidateEvidenceCoverageAt5"] for row in supported) if supported else None,
        "candidateEvidenceCoverageAt5Micro": matched_count / expected_count if expected_count else None,
        "candidateSourceCoverageAt5Macro": mean(row["candidateSourceCoverageAt5"] for row in supported) if supported else None,
        "allCandidateSectionsFoundCount": sum(not row["missingExpectedSectionIds"] for row in supported),
        "anyCandidateSectionFoundCount": sum(bool(row["matchedExpectedSectionIds"]) for row in supported),
        "candidateInsufficiencyAgreement": mean(row["insufficiencyPredictionMatchesCandidate"] for row in completed) if completed else None,
        "supportedCandidatesWithoutEvidence": false_rejections,
        "insufficientCandidatesWithAcceptedEvidence": false_acceptances,
        "candidateEvidenceMissingQuestions": missing,
        "canonicalEvidenceIntegrityRate": sum(evidence_checks) / len(evidence_checks) if evidence_checks else None,
        "canonicalEvidenceChecks": len(evidence_checks),
        "meanRetrievalSeconds": mean(timing) if timing else None,
        "minRetrievalSeconds": min(timing) if timing else None,
        "maxRetrievalSeconds": max(timing) if timing else None,
    }


def write_report(directory: Path, label: str, suffix: str, payload: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"phase-02-retrieval-{label}-{suffix}.json"
    # Preserve failed experiments and reruns: an existing run label is not overwritten.
    if path.exists():
        raise FileExistsError("Evaluation output already exists; choose a new --run-label.")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=PROJECT_ROOT / "knowledge/evaluation/questions.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "docs/evidence/test-results")
    parser.add_argument("--run-label", help="Unique evidence label; default is the real execution timestamp.")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--min-score", type=float, help="Explicit runtime-only diagnostic override; does not alter config or index.")
    args = parser.parse_args()
    now = datetime.now(LOCAL_TIMEZONE)
    label = args.run_label or now.strftime("%Y%m%dT%H%M%S%f")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", label):
        parser.error("--run-label must be a short alphanumeric/hyphen/underscore label.")
    if len(set(args.modes)) != len(args.modes):
        parser.error("Each mode may appear only once.")
    if args.min_score is not None and not 0 <= args.min_score <= 1:
        parser.error("--min-score must be between zero and one.")
    for suffix in (*args.modes, "comparison"):
        if (args.output_dir / f"phase-02-retrieval-{label}-{suffix}.json").exists():
            parser.error("This evidence run already exists; choose a new --run-label.")

    runtime = None
    metadata: dict[str, Any] = {
        "executionStartedAt": now.isoformat(),
        "runLabel": label,
        "evaluationKind": "local_embedding_retrieval_candidates",
        "annotationScope": ANNOTATION_STATUS,
        "humanGoldLabels": False,
        "llmProviderInvoked": False,
        "topK": 5,
        "modeOrder": "alternating per question, after one vector warmup; model loading excluded from per-query latency",
        "thresholdSource": "CLI diagnostic override" if args.min_score is not None else "Settings.retrieval_min_score",
        "parameterSelectionDisclosure": "Threshold reruns on questions used for parameter selection are diagnostics, not independent validation.",
        "questionSetFile": args.questions.name,
        "scriptSHA256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "pythonVersion": platform.python_version(),
        "dependencies": {name: package_version(name) for name in ("sentence-transformers", "torch", "qdrant-client", "pydantic-settings")},
    }
    try:
        questions, question_hash = load_questions(args.questions)
        settings = Settings(**({"retrieval_min_score": args.min_score} if args.min_score is not None else {}))
        metadata.update({"questionSetSHA256": question_hash, "threshold": settings.retrieval_min_score})
        runtime = Runtime(settings)
        load_started = time.perf_counter()
        runtime.open()
        metadata["modelAndIndexLoadSeconds"] = round(time.perf_counter() - load_started, 6)
        if not runtime.search_service:
            result = {"status": "blocked", "metadata": metadata, "diagnostic": runtime.diagnostic, "message": "Knowledge index was not ready; no retrieval results were fabricated."}
            write_report(args.output_dir, label, "comparison", result)
            print(json.dumps({"status": "blocked", "diagnostic": runtime.diagnostic}, ensure_ascii=True))
            return 2

        manifest = runtime.manifest
        metadata["index"] = {key: manifest.get(key) for key in ("generation_id", "corpus_hash", "documents", "chunks", "model_id", "model_revision", "dimension", "distance", "review_scope")}
        chunks = runtime.store.all_chunks()
        section_sources = {chunk["section_id"]: chunk["source_id"] for chunk in chunks}
        annotation_issues = []
        for row in questions:
            for sid in row["expected_section_ids"]:
                if sid not in section_sources or section_sources[sid] not in row["expected_source_ids"]:
                    annotation_issues.append({"questionId": row["id"], "sectionId": sid, "problem": "Candidate section is missing or source does not match the actual index."})
        metadata["annotationIndexIssues"] = annotation_issues
        warmup_started = time.perf_counter()
        runtime.search_service.search(questions[0]["question"], top_k=5, mode="vector")
        metadata["warmupSeconds"] = round(time.perf_counter() - warmup_started, 6)
        results = {mode: [] for mode in args.modes}
        for index, row in enumerate(questions):
            order = args.modes if index % 2 == 0 else list(reversed(args.modes))
            per_question = {}
            for mode in order:
                case = evaluate_case(runtime, row, mode, 5)
                results[mode].append(case)
                per_question[mode] = {"status": case["status"], "uncertain": case.get("uncertain"), "matchedCandidateSections": len(case.get("matchedExpectedSectionIds", []))}
            print(json.dumps({"questionId": row["id"], "results": per_question}, ensure_ascii=True), flush=True)

        metadata["executionFinishedAt"] = datetime.now(LOCAL_TIMEZONE).isoformat()
        summaries = {mode: summarize(cases) for mode, cases in results.items()}
        report_names = {}
        for mode, cases in results.items():
            path = write_report(args.output_dir, label, mode, {"status": "completed", "metadata": metadata, "retrievalMode": mode, "summary": summaries[mode], "cases": cases})
            report_names[mode] = path.name
        comparison = {"status": "completed", "metadata": metadata, "summaries": summaries, "reports": report_names, "latencyLimitation": "Local CPU timing for this run; alternating order reduces but does not eliminate warm/cache effects. No LLM latency or API charges are measured."}
        if set(MODES).issubset(results):
            comparison["hybridMinusVectorCandidateCoverageAt5"] = summaries["hybrid"]["candidateEvidenceCoverageAt5Macro"] - summaries["vector"]["candidateEvidenceCoverageAt5Macro"] if all(summaries[m]["candidateEvidenceCoverageAt5Macro"] is not None for m in MODES) else None
        write_report(args.output_dir, label, "comparison", comparison)
        print(json.dumps({"status": "completed", "summaries": summaries, "reports": report_names}, ensure_ascii=True), flush=True)
        return 1 if annotation_issues or any(s["failedCount"] for s in summaries.values()) else 0
    except Exception as exc:
        # Fatal setup failures remain a real failed artifact, without secret config.
        failure = {"status": "failed", "metadata": metadata, "errorType": type(exc).__name__, "message": "Retrieval evaluation did not complete; no successful results are claimed."}
        if not (args.output_dir / f"phase-02-retrieval-{label}-comparison.json").exists():
            write_report(args.output_dir, label, "comparison", failure)
        print(json.dumps({"status": "failed", "errorType": type(exc).__name__}, ensure_ascii=True))
        return 1
    finally:
        if runtime is not None:
            runtime.close_knowledge()
            runtime.executor.shutdown(wait=True)


if __name__ == "__main__":
    raise SystemExit(main())
