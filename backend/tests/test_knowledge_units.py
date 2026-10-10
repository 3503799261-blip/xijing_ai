"""Unit tests use declared fake encoders; they do not prove real BGE inference.

Qdrant persistence tests use synthetic one-hot vectors, never AI answers.
The separate acceptance run must measure the actual downloaded BGE model.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from backend.app.knowledge.chunking import Chunker
from backend.app.knowledge.embedding import EmbeddingService, QUERY_PREFIX
from backend.app.knowledge.vector_store import VectorStore, point_id


class FakeTokenCounter:
    """Deterministic character counter, deliberately not a real tokenizer."""

    def token_count(self, text: str) -> int:
        return len(text) + 2


class FakeTokenizer:
    def encode(self, text: str, **kwargs: object) -> list[int]:
        assert kwargs == {"add_special_tokens": True, "truncation": False}
        return list(range(len(text) + 2))


class FakeArray:
    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows

    def tolist(self) -> list[list[float]]:
        return self.rows


class FakeSentenceTransformer:
    instances: list[FakeSentenceTransformer] = []

    def __init__(self, path: str, **kwargs: object) -> None:
        assert Path(path).is_dir()
        assert kwargs == {"local_files_only": True, "device": "cpu", "trust_remote_code": False}
        self.tokenizer = FakeTokenizer()
        self.calls: list[list[str]] = []
        self.instances.append(self)

    def get_embedding_dimension(self) -> int:
        return 512

    def encode(self, texts: list[str], **kwargs: object) -> FakeArray:
        assert kwargs["normalize_embeddings"] is True
        self.calls.append(texts)
        return FakeArray([[1.0] + [0.0] * 511 for _ in texts])


class EmbeddingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        (self.path / "model-manifest.json").write_text(
            json.dumps({"revision": "unit-test-declared-fake-revision"}), encoding="utf-8"
        )
        module = types.ModuleType("sentence_transformers")
        module.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
        self.patch = patch.dict("sys.modules", {"sentence_transformers": module})
        self.patch.start()
        self.embedding = EmbeddingService(self.path)

    def tearDown(self) -> None:
        self.patch.stop()
        self.directory.cleanup()

    def test_local_cpu_revision_and_query_prefix(self) -> None:
        self.assertTrue(self.embedding.ready)
        self.assertEqual(self.embedding.model_revision, "unit-test-declared-fake-revision")
        self.assertEqual(len(self.embedding.encode_query(" 生旦净丑是什么？ ")), 512)
        self.assertEqual(FakeSentenceTransformer.instances[-1].calls[-1], [QUERY_PREFIX + "生旦净丑是什么？"])

    def test_document_budget_and_empty_validation(self) -> None:
        self.assertEqual(len(self.embedding.encode_documents(["京剧文化。"])[0]), 512)
        for invalid in ("", " " , "京" * 479):
            with self.assertRaises(ValueError):
                self.embedding.encode_documents([invalid])
        self.assertEqual(self.embedding.encode_documents([]), [])

    def test_query_over_budget_is_rejected_before_encoding(self) -> None:
        calls = len(FakeSentenceTransformer.instances[-1].calls)
        with self.assertRaisesRegex(ValueError, "512"):
            self.embedding.encode_query("京" * 512)
        self.assertEqual(len(FakeSentenceTransformer.instances[-1].calls), calls)

    def test_missing_revision_is_not_silently_invented(self) -> None:
        (self.path / "model-manifest.json").unlink()
        with self.assertRaisesRegex(ValueError, "revision"):
            EmbeddingService(self.path)

    def test_non_finite_and_non_normalized_vectors_are_rejected(self) -> None:
        model = FakeSentenceTransformer.instances[-1]
        for row in ([float("nan")] + [0.0] * 511, [2.0] + [0.0] * 511):
            with patch.object(model, "encode", return_value=FakeArray([row])):
                with self.assertRaises(ValueError):
                    self.embedding.encode_documents(["京剧文化。"])


class ChunkingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunker = Chunker(FakeTokenCounter(), target_chars=60, overlap_chars=10, max_tokens=100)

    def sections(self, text: str) -> list[dict[str, object]]:
        return [{"section_id": "roles", "title": "行当", "locator": "资料第一节", "content": text, "entity_names": ["生", "生", "旦"]}]

    def test_stable_ids_metadata_and_no_unbounded_duplicates(self) -> None:
        sections = self.sections("京剧分为生旦净丑。" * 15)
        one = self.chunker.split_sections("source_roles", "1", sections, category="roles")
        two = self.chunker.split_sections("source_roles", "1", sections, category="roles")
        self.assertEqual(one, two)
        self.assertEqual(len({item["chunk_id"] for item in one}), len(one))
        for chunk in one:
            self.assertEqual(chunk["source_id"], "source_roles")
            self.assertEqual(chunk["document_version"], "1")
            self.assertEqual(chunk["category"], "roles")
            self.assertEqual(chunk["entity_names"], ["生", "旦"])
            self.assertIn("资料第一节", chunk["locator"])
            self.assertLessEqual(chunk["token_count"], 100)

    def test_long_sentence_preserves_every_character_without_truncation(self) -> None:
        text = "".join(chr(0x4E00 + index) for index in range(310))
        chunker = Chunker(FakeTokenCounter(), overlap_chars=0, max_tokens=100)
        chunks = chunker.split_sections("source", "1", self.sections(text))
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunk["content"] for chunk in chunks), text)
        self.assertTrue(all(chunk["token_count"] <= 100 for chunk in chunks))

    def test_overlap_is_bounded_by_real_token_counter(self) -> None:
        text = "甲" * 70 + "。" + "乙" * 70 + "。" + "丙" * 70 + "。"
        chunks = self.chunker.split_sections("source", "1", self.sections(text))
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(chunks[1]["content"].startswith("甲" * 9 + "。"))
        self.assertTrue(all(chunk["token_count"] <= 100 for chunk in chunks))

    def test_empty_content_is_skipped_and_malformed_sections_rejected(self) -> None:
        self.assertEqual(self.chunker.split_sections("source", "1", self.sections("  \n ")), [])
        with self.assertRaises(ValueError):
            self.chunker.split_sections("source", "1", [{"title": "bad", "content": 123}])


@unittest.skipUnless(importlib.util.find_spec("qdrant_client") is not None, "Qdrant dependency not installed; no persistence result claimed")
class VectorPersistenceTests(unittest.TestCase):
    def vector(self, axis: int) -> list[float]:
        result = [0.0] * 512
        result[axis] = 1.0
        return result

    def chunk(self, identifier: str, category: str) -> dict[str, str]:
        return {"chunk_id": identifier, "source_id": "source", "document_version": "1", "section_id": "section", "category": category}

    def test_actual_qdrant_persistence_and_idempotent_upsert_with_synthetic_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vectors"
            chunks = [self.chunk("one", "roles"), self.chunk("two", "costumes")]
            vectors = [self.vector(0), self.vector(1)]
            with VectorStore(path) as store:
                store.upsert(chunks, vectors)
                store.upsert(chunks, vectors)
                self.assertEqual(store.count(), 2)
                self.assertEqual(store.search(vectors[0])[0]["chunk_id"], "one")
                self.assertEqual(store.search(vectors[0], category="costumes")[0]["chunk_id"], "two")
            with VectorStore(path) as reopened:
                self.assertEqual(reopened.count(), 2)
                self.assertEqual(reopened.search(vectors[0])[0]["source_id"], "source")

    def test_owner_thread_and_invalid_vectors_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, VectorStore(Path(directory) / "vectors") as store:
            errors: list[str] = []

            def other_thread() -> None:
                try:
                    store.count()
                except RuntimeError as exc:
                    errors.append(str(exc))

            thread = threading.Thread(target=other_thread)
            thread.start()
            thread.join()
            self.assertEqual(len(errors), 1)
            with self.assertRaises(ValueError):
                store.search([0.0] * 512)
            with self.assertRaises(ValueError):
                store.search([1.0, 0.0])

    def test_stable_uuid_and_existing_dimension_check(self) -> None:
        self.assertEqual(point_id("one"), point_id("one"))
        self.assertNotEqual(point_id("one"), point_id("two"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vectors"
            with VectorStore(path):
                pass
            with self.assertRaises(ValueError):
                VectorStore(path, dimension=256)


if __name__ == "__main__":
    unittest.main()
