"""Small, persistent Qdrant local store with one owner thread."""

from __future__ import annotations

import math
import threading
import uuid
from pathlib import Path
from typing import Any

from .embedding import EMBEDDING_DIMENSION


COLLECTION_NAME = "opera_chunks"


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "xijing-ai:chunk:" + chunk_id))


class VectorStore:
    def __init__(self, path: Path, dimension: int = EMBEDDING_DIMENSION) -> None:
        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension < 1:
            raise ValueError("向量维度无效。")
        from qdrant_client import QdrantClient, models

        self.path = Path(path).resolve()
        self.dimension = dimension
        self._owner_thread = threading.get_ident()
        self._closed = False
        self._models = models
        self._client = QdrantClient(path=str(self.path))
        try:
            if not self._client.collection_exists(COLLECTION_NAME):
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
                )
            else:
                vectors = self._client.get_collection(COLLECTION_NAME).config.params.vectors
                if isinstance(vectors, dict) or vectors is None:
                    raise ValueError("已有索引的向量配置与当前模型不兼容。")
                if vectors.size != dimension or vectors.distance != models.Distance.COSINE:
                    raise ValueError("已有索引的维度或距离与当前模型不兼容，请重建索引。")
        except Exception:
            self._client.close()
            self._closed = True
            raise

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("本地向量存储已关闭。")
        if threading.get_ident() != self._owner_thread:
            raise RuntimeError("本地向量存储必须由创建它的同一线程使用。")

    def _vector(self, vector: list[float]) -> list[float]:
        if not isinstance(vector, (list, tuple)) or len(vector) != self.dimension:
            raise ValueError("向量维度与索引不一致。")
        try:
            values = [float(value) for value in vector]
        except (TypeError, ValueError) as exc:
            raise ValueError("向量必须由数值组成。") from exc
        if not all(math.isfinite(value) for value in values) or not any(values):
            raise ValueError("向量必须有限且非零。")
        return values

    def upsert(self, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        self._ensure_open()
        if len(chunks) != len(vectors):
            raise ValueError("片段数量与向量数量不一致。")
        points = []
        for chunk, vector in zip(chunks, vectors):
            required = ("chunk_id", "source_id", "document_version", "section_id")
            if any(not isinstance(chunk.get(key), str) or not chunk[key].strip() for key in required):
                raise ValueError("片段缺少真实的 ID 或版本元数据。")
            payload = {key: chunk[key] for key in required}
            if chunk.get("category") is not None:
                payload["category"] = chunk["category"]
            points.append(
                self._models.PointStruct(
                    id=point_id(chunk["chunk_id"]), vector=self._vector(vector), payload=payload
                )
            )
        if points:
            self._client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)

    def search(
        self, vector: list[float], limit: int = 5, category: str | None = None
    ) -> list[dict[str, Any]]:
        self._ensure_open()
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
            raise ValueError("检索数量必须在 1 到 10 之间。")
        query_filter = None
        if category is not None:
            if not isinstance(category, str) or not category.strip():
                raise ValueError("检索分类不能为空。")
            query_filter = self._models.Filter(
                must=[self._models.FieldCondition(key="category", match=self._models.MatchValue(value=category))]
            )
        response = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=self._vector(vector),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
        )
        result = []
        for point in response.points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise RuntimeError("向量检索结果缺少片段关联，请核查索引。")
            result.append({**payload, "chunk_id": chunk_id, "score": float(point.score)})
        return result

    def count(self) -> int:
        self._ensure_open()
        return self._client.count(collection_name=COLLECTION_NAME, exact=True).count

    def validate_links(self, chunks: list[dict[str, Any]]) -> None:
        self._ensure_open()
        points = self._client.retrieve(collection_name=COLLECTION_NAME, ids=[point_id(c['chunk_id']) for c in chunks], with_payload=True, with_vectors=False)
        actual = {str(p.id): p.payload or {} for p in points}
        for chunk in chunks:
            payload = actual.get(point_id(chunk['chunk_id']))
            if payload is None or any(payload.get(k) != chunk[k] for k in ('chunk_id', 'source_id', 'section_id', 'document_version')):
                raise ValueError('向量与SQLite片段来源/版本关联不一致，不能激活索引。')

    def close(self) -> None:
        if self._closed:
            return
        self._ensure_open()
        self._client.close()
        self._closed = True

    def __enter__(self) -> VectorStore:
        self._ensure_open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
