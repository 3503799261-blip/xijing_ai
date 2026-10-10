"""Free, isolated comparison of body embeddings and metadata-context embeddings.

The live canonical SQLite is opened read-only. Main Qdrant and its owner lock
are never opened. Both experimental Qdrant directories live outside the site.
No LLM, HTTP request, fallback encoder, label edit, or active-index write.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import quote

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.knowledge.embedding import EmbeddingService
from backend.app.knowledge.vector_store import VectorStore
from backend.scripts.evaluate_retrieval import load_questions, summarize

TZ = timezone(timedelta(hours=8), "Asia/Shanghai")
VARIANTS = ("content", "title_section_content")


def now() -> str:
    return datetime.now(TZ).isoformat()


def canonical_snapshot(settings):
    active = settings.rag_data_dir / "active.json"
    active_raw = active.read_bytes()
    manifest = json.loads(active_raw.decode("utf-8"))
    generation = manifest["generation_id"]
    if not isinstance(generation, str) or not re.fullmatch(r"gen-[A-Za-z0-9_-]+", generation):
        raise ValueError("Invalid active generation.")
    database = (settings.rag_data_dir / "generations" / generation / "knowledge.sqlite3").resolve()
    if settings.rag_data_dir.resolve() not in database.parents or not database.is_file():
        raise ValueError("Canonical database is unavailable.")
    connection = sqlite3.connect("file:" + quote(database.as_posix(), safe="/:") + "?mode=ro", uri=True)
    try:
        connection.execute("BEGIN")
        rows = connection.execute("SELECT c.data_json,s.data_json FROM chunks c JOIN sources s USING(source_id) ORDER BY c.chunk_id").fetchall()
        chunks = [{**json.loads(chunk_json), "source": json.loads(source_json)} for chunk_json, source_json in rows]
    finally:
        connection.close()
    if not chunks or len(chunks) != manifest["chunks"]:
        raise ValueError("Canonical snapshot count is inconsistent.")
    return active, manifest, chunks, sha256(active_raw).hexdigest(), sha256(database.read_bytes()).hexdigest(), database


def case_result(row, variant, hits, by_id, threshold, embedding_seconds, search_seconds):
    expected_sections = set(row["expected_section_ids"])
    expected_sources = set(row["expected_source_ids"])
    evidence, contexts = [], []
    integrity = []
    for rank, hit in enumerate(hits, start=1):
        chunk = by_id[hit["chunk_id"]]
        source = chunk["source"]
        valid = all(hit[key] == chunk[key] for key in ("chunk_id", "source_id", "section_id", "document_version"))
        if not valid:
            raise ValueError("Experimental payload changed a canonical evidence association.")
        accepted = hit["score"] >= threshold
        contexts.append({"chunkId": hit["chunk_id"], "sourceId": chunk["source_id"], "sectionId": chunk["section_id"], "sectionTitle": chunk["section"], "vectorRank": rank, "vectorScore": hit["score"], "acceptedAsEvidence": accepted, "matchesCandidateSection": chunk["section_id"] in expected_sections})
        if accepted:
            evidence.append({"id": chunk["chunk_id"], "sourceId": chunk["source_id"], "sectionId": chunk["section_id"], "title": source["title"], "locator": chunk["locator"], "url": source["source_url"], "excerpt": chunk["content"], "contentKind": source["content_kind"], "vectorScore": hit["score"]})
            integrity.append(valid)
    returned_sections = {hit["sectionId"] for hit in evidence}
    returned_sources = {hit["sourceId"] for hit in evidence}
    matched = returned_sections & expected_sections
    uncertain = not bool(evidence)
    return {
        "id": row["id"], "question": row["question"], "status": "completed", "variant": variant,
        "annotationStatus": row["annotation_status"], "expectedFacts": row["expected_facts"],
        "expectedSectionIds": row["expected_section_ids"], "expectedSourceIds": row["expected_source_ids"],
        "expectInsufficient": row["expect_insufficient"], "uncertain": uncertain,
        "insufficiencyPredictionMatchesCandidate": uncertain == row["expect_insufficient"],
        "matchedExpectedSectionIds": sorted(matched), "missingExpectedSectionIds": sorted(expected_sections - returned_sections),
        "returnedSectionIds": sorted(returned_sections), "returnedSourceIds": sorted(returned_sources),
        "candidateEvidenceCoverageAt5": len(matched) / len(expected_sections) if expected_sections else None,
        "candidateSourceCoverageAt5": len(returned_sources & expected_sources) / len(expected_sources) if expected_sources else None,
        "canonicalEvidenceChecks": integrity, "evidence": evidence, "candidateScoreContexts": contexts,
        "threshold": threshold, "queryEmbeddingSeconds": embedding_seconds, "vectorSearchSeconds": search_seconds,
        "elapsedSeconds": round(embedding_seconds + search_seconds, 6),
    }


def run(args):
    settings = Settings()
    experiment_dir = settings.rag_data_dir.parent / "embedding-context-experiments" / args.label
    if experiment_dir.resolve() == PROJECT_ROOT or PROJECT_ROOT in experiment_dir.resolve().parents:
        raise ValueError("Experiment must be outside the website root.")
    if experiment_dir.exists() or args.output.exists():
        raise FileExistsError("Use a fresh experiment label and output path.")
    questions, question_hash = load_questions(args.questions)
    holdout, holdout_hash = load_questions(args.holdout)
    recommended = [{
        "id": "opera-recommended-shengdanjingchou", "question": "京剧中的生旦净丑有什么区别？",
        "category": "原有推荐问题", "annotation_status": "assistant_source_checked_candidate", "expect_insufficient": False,
        "expected_facts": ["解释生、旦、净、丑的角色类型与表演差异；不能把角色行当与演员性别或流派混为一谈。"],
        "expected_source_ids": ["fujian-roles"],
        "expected_section_ids": ["fujian-roles-system", "fujian-roles-sheng-dan", "fujian-roles-jing", "fujian-roles-chou"],
    }]
    groups = {"original20": questions, "previous_five_question_holdout": holdout, "original_recommended_question": recommended}
    active, manifest, chunks, active_hash, database_hash, database = canonical_snapshot(settings)
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    expected_ids = {sid for rows in groups.values() for row in rows for sid in row["expected_section_ids"]}
    if expected_ids - {chunk["section_id"] for chunk in chunks}:
        raise ValueError("Candidate annotations do not match the actual snapshot.")
    inputs = {
        "content": [chunk["content"] for chunk in chunks],
        "title_section_content": [chunk["source"]["title"] + "\n" + chunk["section"] + "\n" + chunk["content"] for chunk in chunks],
    }
    metadata = {
        "label": args.label, "startedAt": now(), "threshold": args.min_score, "topK": 5,
        "indexSnapshot": {key: manifest.get(key) for key in ("generation_id", "corpus_hash", "chunks", "documents", "model_id", "model_revision", "dimension")},
        "canonicalDatabaseSHA256": database_hash, "mainActiveManifestSHA256Before": active_hash,
        "questionSetSHA256": question_hash, "previousHoldoutSHA256": holdout_hash,
        "scriptSHA256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "mainDatabaseMode": "read-only snapshot; main Qdrant and index-owner lock are not opened",
        "llmRequests": 0, "httpRequests": 0, "humanGoldLabels": False,
        "labelScope": "Assistant source-checked candidate evidence, not human Recall@5 or answer correctness.",
        "selectionLimitation": "The five questions were held out of the initial threshold selection but have already been evaluated. Reusing them to choose this embedding context is not independent validation; the corpus and assistant annotator are shared.",
        "vectorTextStrategies": {"content": "canonical content only", "title_section_content": "source.title + newline + chunk.section + newline + canonical content"},
        "canonicalTextAndIdsUnchanged": True,
    }
    experiment_dir.mkdir(parents=True)
    load_started = time.perf_counter()
    embedding = EmbeddingService(settings.embedding_model_path)
    metadata["modelLoadSeconds"] = round(time.perf_counter() - load_started, 6)
    if embedding.model_revision != manifest["model_revision"]:
        raise ValueError("Experimental encoder revision differs from the active baseline.")
    metadata["realModelRevision"] = embedding.model_revision
    metadata["vectorBuild"] = {}
    stores = {}
    results = {variant: {group: [] for group in groups} for variant in VARIANTS}
    try:
        for variant in VARIANTS:
            started = time.perf_counter()
            vectors = embedding.encode_documents(inputs[variant])
            stores[variant] = VectorStore(experiment_dir / variant / "qdrant")
            stores[variant].upsert(chunks, vectors)
            stores[variant].validate_links(chunks)
            if stores[variant].count() != len(chunks):
                raise ValueError("Experimental vector count differs from the canonical snapshot.")
            metadata["vectorBuild"][variant] = {"count": len(vectors), "elapsedSeconds": round(time.perf_counter() - started, 6), "inputSHA256": sha256(json.dumps(inputs[variant], ensure_ascii=False).encode()).hexdigest(), "minTokens": min(embedding.token_count(text) for text in inputs[variant]), "maxTokens": max(embedding.token_count(text) for text in inputs[variant])}
        for group, rows in groups.items():
            for index, row in enumerate(rows):
                started = time.perf_counter()
                vector = embedding.encode_query(row["question"])
                embedding_seconds = round(time.perf_counter() - started, 6)
                for variant in VARIANTS if index % 2 == 0 else tuple(reversed(VARIANTS)):
                    started = time.perf_counter()
                    hits = stores[variant].search(vector, limit=5)
                    search_seconds = round(time.perf_counter() - started, 6)
                    results[variant][group].append(case_result(row, variant, hits, by_id, args.min_score, embedding_seconds, search_seconds))
                print(json.dumps({"questionId": row["id"], "group": group, "matches": {variant: len(results[variant][group][-1]["matchedExpectedSectionIds"]) for variant in VARIANTS}}, ensure_ascii=True), flush=True)
    finally:
        for store in stores.values():
            store.close()
    metadata["finishedAt"] = now()
    metadata["mainActiveManifestSHA256After"] = sha256(active.read_bytes()).hexdigest()
    metadata["mainActiveManifestUnchangedDuringExperiment"] = metadata["mainActiveManifestSHA256After"] == active_hash
    metadata["mainCanonicalDatabaseUnchangedDuringExperiment"] = sha256(database.read_bytes()).hexdigest() == database_hash
    summaries = {variant: {group: summarize(cases) for group, cases in grouped.items()} for variant, grouped in results.items()}
    comparison = {}
    for group in groups:
        a, b = summaries["content"][group], summaries["title_section_content"][group]
        comparison[group] = {
            "contextMinusContentCandidateCoverageAt5": b["candidateEvidenceCoverageAt5Macro"] - a["candidateEvidenceCoverageAt5Macro"],
            "contentFalseInsufficiency": a["supportedCandidatesWithoutEvidence"], "contextFalseInsufficiency": b["supportedCandidatesWithoutEvidence"],
            "contentInsufficientCasesWithAcceptedEvidence": a["insufficientCandidatesWithAcceptedEvidence"],
            "contextInsufficientCasesWithAcceptedEvidence": b["insufficientCandidatesWithAcceptedEvidence"],
        }
    report = {"status": "completed", "metadata": metadata, "summaries": summaries, "comparisons": comparison, "cases": results,
              "timingLimitation": "Each query is encoded once and shared across the two stores. These are local CPU query/search timings; they do not measure LLM latency or paid costs."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        target.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "summaries": summaries, "comparisons": comparison}, ensure_ascii=True), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f"))
    parser.add_argument("--questions", type=Path, default=PROJECT_ROOT / "knowledge/evaluation/questions.json")
    parser.add_argument("--holdout", type=Path, default=PROJECT_ROOT / "knowledge/evaluation/holdout-questions.json")
    parser.add_argument("--min-score", type=float, default=0.57)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.label) or not 0 <= args.min_score <= 1:
        parser.error("Use a unique safe label and a threshold between zero and one.")
    args.output = args.output or PROJECT_ROOT / "docs/evidence/test-results" / f"phase-02-embedding-context-{args.label}.json"
    try:
        run(args)
        return 0
    except Exception as exc:
        failure = {"status": "failed", "label": args.label, "executedAt": now(), "errorType": type(exc).__name__, "llmRequests": 0, "message": "Isolated experiment did not finish; no successful result is claimed and main index was not activated or rewritten."}
        if not args.output.exists():
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as target:
                target.write(json.dumps(failure, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(failure, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
