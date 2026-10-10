"""OFFLINE ingestion tests: fake encoder, real temporary SQLite/Qdrant.

All documents and vectors are declared unit fixtures, not real corpus evidence.
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import portalocker
import pytest
from pydantic import SecretStr

from backend.app.config import Settings
from backend.app.knowledge.store import KnowledgeStore
from backend.app.knowledge.vector_store import VectorStore
from backend.scripts import ingest


class FakeEmbedding:
    model_revision = "unit-only-fake-revision"
    constructed = 0

    def __init__(self, model_path):
        self.constructed += 1

    def token_count(self, text):
        return len(text) + 2

    def encode_documents(self, texts):
        rows = []
        for text in texts:
            vector = [0.0] * 512
            vector[int(hashlib.sha256(text.encode()).hexdigest()[:4], 16) % 512] = 1.0
            rows.append(vector)
        return rows


def document(identifier="unit-source", text="此为单元测试资料，不代表文化知识。", version="1"):
    return {
        "source": {
            "source_id": identifier, "title": "单元测试资料", "category": "history",
            "author_or_organization": "unit-test-fixture", "source_url": "https://example.invalid/unit-only",
            "publication_date": None, "collected_at": "2026-10-10", "license_status": "unit-fixture-only",
            "review_status": "source_checked_by_assistant", "document_version": version,
            "content_kind": "original_fact_summary", "scope": "仅离线单元测试",
            "license_url": "https://example.invalid/unit-only-license", "redistribution_allowed": True,
            "external_llm_allowed": True,
        },
        "sections": [{"section_id": "unit-section", "title": "单元测试节", "locator": "单元测试首节", "content": text, "entity_names": ["单元测试"]}],
    }


def corpus_with(tmp_path, documents):
    corpus = tmp_path / "unit-corpus"
    directory = corpus / "documents"
    directory.mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(documents):
        (directory / f"{index}.json").write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")
    return corpus


def settings_for_test(tmp_path):
    model = tmp_path / "unit-fake-model"
    model.mkdir()
    (model / "model-manifest.json").write_text(json.dumps({"revision": FakeEmbedding.model_revision}), encoding="utf-8")
    return Settings(_env_file=None, deepseek_api_key=SecretStr(""), rag_data_dir=tmp_path / "runtime", embedding_model_path=model)


def test_source_provenance_and_content_hash_are_actual(tmp_path):
    original = document()
    corpus = corpus_with(tmp_path, [original])
    loaded = ingest.load_documents(corpus)
    assert loaded[0]["source"]["content_hash"] == ingest.digest(original["sections"])
    assert loaded[0]["sections"] == original["sections"]


@pytest.mark.parametrize("field,value", [("source_url", 123), ("source_url", "https://"), ("source_url", "https://user:password@example.invalid"), ("title", 123), ("category", []), ("redistribution_allowed", False), ("external_llm_allowed", "true"), ("review_status", "unreviewed")])
def test_invalid_source_metadata_is_rejected_as_validation_failure(tmp_path, field, value):
    item = document()
    item["source"][field] = value
    corpus = corpus_with(tmp_path, [item])
    with pytest.raises(ValueError):
        ingest.load_documents(corpus)


def test_duplicate_source_and_missing_provenance_are_rejected(tmp_path):
    corpus = corpus_with(tmp_path, [document(), document()])
    with pytest.raises(ValueError, match="Duplicate"):
        ingest.load_documents(corpus)
    broken = document()
    del broken["source"]["license_status"]
    corpus_with(tmp_path, [broken])
    with pytest.raises(ValueError):
        ingest.load_documents(corpus)


def test_idempotent_rebuild_restart_and_actual_id_association_with_fake_encoder(tmp_path):
    corpus = corpus_with(tmp_path, [document()])
    configuration = settings_for_test(tmp_path)
    with patch.object(ingest, "EmbeddingService", FakeEmbedding):
        first = ingest.build(corpus, configuration)
        repeated = ingest.build(corpus, configuration)
        rebuilt = ingest.build(corpus, configuration, rebuild=True)
    assert first["status"] == rebuilt["status"] == "built"
    assert repeated["status"] == "unchanged" and repeated["added"] == 0
    assert repeated["generation_id"] == first["generation_id"]
    assert rebuilt["generation_id"] != first["generation_id"]
    assert first["chunks"] == rebuilt["chunks"] == 1
    target = configuration.rag_data_dir / "generations" / rebuilt["generation_id"]
    store = KnowledgeStore(target / "knowledge.sqlite3")
    try:
        chunk = store.all_chunks()[0]
        encoded = FakeEmbedding(configuration.embedding_model_path).encode_documents([chunk["content"]])[0]
        with VectorStore(target / "qdrant") as vectors:
            hit = vectors.search(encoded)[0]
            assert hit["chunk_id"] == chunk["chunk_id"]
            assert hit["source_id"] == store.chunk(hit["chunk_id"])["source_id"]
            assert vectors.count() == store.count() == 1
    finally:
        store.close()


def test_updated_document_activates_new_index_and_keeps_old_generation(tmp_path):
    corpus = corpus_with(tmp_path, [document(text="单元测试旧文本。")])
    configuration = settings_for_test(tmp_path)
    with patch.object(ingest, "EmbeddingService", FakeEmbedding):
        old = ingest.build(corpus, configuration)
        corpus_with(tmp_path, [document(text="单元测试新文本。", version="2")])
        new = ingest.build(corpus, configuration)
    assert new["generation_id"] != old["generation_id"]
    assert json.loads((configuration.rag_data_dir / "active.json").read_text(encoding="utf-8"))["generation_id"] == new["generation_id"]
    old_path = configuration.rag_data_dir / "generations" / old["generation_id"]
    assert (old_path / "manifest.json").is_file()
    store = KnowledgeStore(configuration.rag_data_dir / "generations" / new["generation_id"] / "knowledge.sqlite3")
    try:
        assert store.all_chunks()[0]["content"] == "单元测试新文本。"
        assert store.all_chunks()[0]["document_version"] == "2"
    finally:
        store.close()


def test_failed_generation_does_not_replace_active_manifest_and_releases_lock(tmp_path):
    corpus = corpus_with(tmp_path, [document()])
    configuration = settings_for_test(tmp_path)
    with patch.object(ingest, "EmbeddingService", FakeEmbedding):
        ingest.build(corpus, configuration)
        active = configuration.rag_data_dir / "active.json"
        previous = active.read_bytes()
        with patch.object(FakeEmbedding, "encode_documents", side_effect=RuntimeError("offline encoder failure")):
            with pytest.raises(RuntimeError, match="offline encoder"):
                ingest.build(corpus, configuration, rebuild=True)
        assert active.read_bytes() == previous
        recovered = ingest.build(corpus, configuration, rebuild=True)
        assert recovered["status"] == "built"


def test_empty_or_repeated_content_does_not_grow_active_evidence(tmp_path):
    item = document()
    duplicate = document(identifier="unit-second-source")
    corpus = corpus_with(tmp_path, [item, duplicate])
    configuration = settings_for_test(tmp_path)
    with patch.object(ingest, "EmbeddingService", FakeEmbedding):
        result = ingest.build(corpus, configuration)
        assert result["documents"] == 2 and result["chunks"] == 1
        assert result["duplicates_skipped"] == 1
        corpus_with(tmp_path, [document(text="  \n "), document(identifier="unit-second-source", text="")])
        with pytest.raises(ValueError):
            ingest.build(corpus, configuration, rebuild=True)


def test_shared_lock_prevents_builder_and_live_owner_overlap(tmp_path):
    corpus = corpus_with(tmp_path, [document()])
    configuration = settings_for_test(tmp_path)
    with ingest.index_lock(configuration.rag_data_dir):
        with patch.object(ingest, "EmbeddingService", FakeEmbedding):
            with pytest.raises(portalocker.exceptions.LockException):
                ingest.build(corpus, configuration)


def test_equal_count_wrong_vector_mapping_is_rejected_before_activation(tmp_path):
    class WrongAssociationStore(VectorStore):
        def upsert(self, chunks, vectors):
            wrong = [{**chunk, "source_id": "wrong-unit-source", "chunk_id": "wrong-unit-chunk"} for chunk in chunks]
            super().upsert(wrong, vectors)

    corpus = corpus_with(tmp_path, [document()])
    configuration = settings_for_test(tmp_path)
    with patch.object(ingest, "EmbeddingService", FakeEmbedding), patch.object(ingest, "VectorStore", WrongAssociationStore):
        with pytest.raises(ValueError):
            ingest.build(corpus, configuration)
    assert not (configuration.rag_data_dir / "active.json").exists()
