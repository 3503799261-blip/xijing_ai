"""Offline, CPU-only BGE embeddings. There is no fallback encoder."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
EMBEDDING_DIMENSION = 512
MAX_MODEL_TOKENS = 512
MAX_DOCUMENT_TOKENS = 480


class EmbeddingService:
    """Load the approved model from a local directory, without network access.

    ``model-manifest.json`` records the downloaded Hugging Face revision.
    An explicit revision can also be supplied by the application configuration.
    Model loading and calls belong on the application's dedicated executor.
    """

    def __init__(self, model_path: Path, model_revision: str | None = None) -> None:
        self.ready = False
        self.model_path = Path(model_path).resolve()
        if not self.model_path.is_dir():
            raise ValueError("本地 Embedding 模型目录不存在，请先完成模型下载。")
        self.model_revision = self._read_revision(model_revision)

        # Import only when constructing the real service. Unit tests can exercise
        # chunking without importing PyTorch or downloading model weights.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            str(self.model_path),
            local_files_only=True,
            device="cpu",
            trust_remote_code=False,
        )
        if self._model.get_embedding_dimension() != EMBEDDING_DIMENSION:
            raise ValueError("本地 Embedding 模型的向量维度不是约定的 512 维。")
        self._model.max_seq_length = MAX_MODEL_TOKENS
        self._tokenizer = self._model.tokenizer
        self.ready = True

    def _read_revision(self, explicit: str | None) -> str:
        if explicit is not None:
            if not isinstance(explicit, str) or not explicit.strip():
                raise ValueError("Embedding 模型 revision 配置无效。")
            return explicit.strip()
        for filename in ("model-manifest.json", "manifest.json"):
            path = self.model_path / filename
            if not path.is_file():
                continue
            try:
                manifest: Any = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("Embedding 模型 revision 清单无法读取。") from exc
            if not isinstance(manifest, dict):
                raise ValueError("Embedding 模型 revision 清单格式无效。")
            revision = manifest.get("revision") or manifest.get("model_revision")
            if isinstance(revision, str) and revision.strip():
                return revision.strip()
            raise ValueError("Embedding 模型清单未记录实际下载 revision。")
        raise ValueError("Embedding 模型缺少实际下载 revision 记录。")

    def token_count(self, text: str) -> int:
        if not isinstance(text, str):
            raise ValueError("Embedding 输入必须是文本。")
        # Include [CLS]/[SEP]. Explicit truncation=False prevents a silent loss
        # of evidence, even though the tokenizer may warn on overlong input.
        return len(self._tokenizer.encode(text, add_special_tokens=True, truncation=False))

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list):
            raise ValueError("待编码资料必须是文本列表。")
        if not texts:
            return []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("资料片段不能为空。")
            if self.token_count(text) > MAX_DOCUMENT_TOKENS:
                raise ValueError("资料片段超过 480 tokens，请重新分块。")
        return self._encode(texts)

    def encode_query(self, question: str) -> list[float]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("问题不能为空。")
        query = QUERY_PREFIX + question.strip()
        if self.token_count(query) > MAX_MODEL_TOKENS:
            raise ValueError("问题加检索指令后超过 512 tokens，请缩短问题。")
        return self._encode([query])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        encoded = self._model.encode(
            texts,
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        vectors = encoded.tolist()
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("Embedding 返回的向量数量与输入不一致。")
        result: list[list[float]] = []
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION:
                raise ValueError("Embedding 返回的向量维度无效。")
            try:
                values = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise ValueError("Embedding 返回了非数值向量。") from exc
            if not all(math.isfinite(value) for value in values):
                raise ValueError("Embedding 返回了非有限向量。")
            norm = math.sqrt(sum(value * value for value in values))
            if not math.isclose(norm, 1.0, rel_tol=0.005, abs_tol=0.005):
                raise ValueError("Embedding 返回的向量未正确归一化。")
            result.append(values)
        return result
