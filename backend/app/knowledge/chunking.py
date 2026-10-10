"""Deterministic chapter/sentence chunking with a real-tokenizer budget."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Protocol

from .embedding import MAX_DOCUMENT_TOKENS


class TokenCounter(Protocol):
    def token_count(self, text: str) -> int: ...


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class Chunker:
    def __init__(
        self,
        embedding: TokenCounter,
        target_chars: int = 350,
        overlap_chars: int = 70,
        max_tokens: int = MAX_DOCUMENT_TOKENS,
    ) -> None:
        if target_chars < 1 or overlap_chars < 0 or not 1 <= max_tokens <= MAX_DOCUMENT_TOKENS:
            raise ValueError("分块参数无效。")
        self.embedding = embedding
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars
        self.max_tokens = max_tokens

    def split_sections(
        self,
        source_id: str,
        version: str,
        sections: list[dict[str, Any]],
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("资料 source_id 不能为空。")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("资料 document_version 不能为空。")
        if not isinstance(sections, list):
            raise ValueError("资料 sections 必须是列表。")
        chunks: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ordinal, section in enumerate(sections, start=1):
            if not isinstance(section, dict) or not isinstance(section.get("content"), str):
                raise ValueError("资料章节必须包含文本 content。")
            content = _normalize(section["content"])
            if not content:
                continue
            title = section.get("title") or section.get("section")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("资料章节必须包含真实标题。")
            title = title.strip()
            section_id = section.get("section_id") or section.get("id")
            if not section_id:
                section_id = "section_" + _sha256(f"{source_id}\n{ordinal}\n{title}")[:24]
            if not isinstance(section_id, str):
                raise ValueError("章节 section_id 必须是文本。")
            locator = section.get("locator") or title
            if not isinstance(locator, str):
                raise ValueError("章节 locator 必须是文本。")
            entities = section.get("entity_names", [])
            if not isinstance(entities, list) or any(not isinstance(item, str) for item in entities):
                raise ValueError("章节 entity_names 必须是文本列表。")
            bodies = self._bodies(content)
            previous = ""
            for index, body in enumerate(bodies, start=1):
                tail = previous[-self.overlap_chars:] if self.overlap_chars else ""
                while tail and self.embedding.token_count(tail + "\n" + body) > self.max_tokens:
                    tail = tail[1:]
                chunk_content = (tail + "\n" + body).strip() if tail else body
                previous = body
                token_count = self.embedding.token_count(chunk_content)
                if token_count > self.max_tokens:
                    raise ValueError("资料分块超过实际 tokenizer 预算，请检查分块参数。")
                content_hash = _sha256(chunk_content)
                if content_hash in seen:
                    continue
                seen.add(content_hash)
                chunk_id = "chunk_" + _sha256(f"{source_id}\n{section_id}\n{content_hash}")
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "source_id": source_id,
                        "document_version": version,
                        "content_hash": content_hash,
                        "content": chunk_content,
                        "section_id": section_id,
                        "section": title,
                        "locator": f"{locator} · 入库片段 {index}/{len(bodies)}",
                        "category": category if category is not None else section.get("category"),
                        "entity_names": list(dict.fromkeys(entities)),
                        "token_count": token_count,
                    }
                )
        return chunks

    def _bodies(self, text: str) -> list[str]:
        sentences = [part.strip() for part in re.split(r"(?<=[。！？!?；;])|\n+", text) if part.strip()]
        units: list[str] = []
        for sentence in sentences:
            units.extend(self._split_long(sentence))
        result: list[str] = []
        current = ""
        for unit in units:
            candidate = current + "\n" + unit if current else unit
            if current and (
                len(current) >= self.target_chars
                or self.embedding.token_count(candidate) > self.max_tokens
            ):
                result.append(current)
                current = unit
            else:
                current = candidate
        if current:
            result.append(current)
        return result

    def _split_long(self, text: str) -> list[str]:
        parts: list[str] = []
        remaining = text
        while remaining:
            if self.embedding.token_count(remaining) <= self.max_tokens:
                parts.append(remaining)
                break
            # Find the largest safe prefix, then prefer a nearby word/phrase
            # boundary. A long sentence has no permission to truncate evidence.
            low, high = 1, len(remaining)
            end = 0
            while low <= high:
                middle = (low + high) // 2
                if self.embedding.token_count(remaining[:middle]) <= self.max_tokens:
                    end = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if end == 0:
                raise ValueError("分块 token 预算不足以容纳一个字符。")
            boundaries = list(re.finditer(r"[，、,：:\s]", remaining[:end]))
            if boundaries and boundaries[-1].end() >= end // 2:
                end = boundaries[-1].end()
            # Token counts can change at a different word boundary. Check the
            # final prefix rather than assuming the binary-search count holds.
            while end > 0 and self.embedding.token_count(remaining[:end].strip()) > self.max_tokens:
                end -= 1
            if end == 0:
                raise ValueError("分块 token 预算不足以容纳一个字符。")
            part = remaining[:end].strip()
            if part:
                parts.append(part)
            remaining = remaining[end:].lstrip()
        return parts
