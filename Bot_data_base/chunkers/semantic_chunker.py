from __future__ import annotations

import re
from typing import List

from models.universal_block import UniversalBlock
from utils.text_utils import count_tokens, clean_text, split_into_paragraphs


class SemanticChunker:
    def __init__(self, config: dict):
        self.config = config or {}
        self._yt_cfg = self._extract_youtube_config(self.config)

    def chunk(self, text: str, author: str, source_title: str, source_id: str) -> List[UniversalBlock]:
        cleaned = clean_text(text)
        if not cleaned:
            return []

        min_tokens = int(self._yt_cfg.get("min_tokens", 200))
        max_tokens = int(self._yt_cfg.get("max_tokens", 800))

        paragraphs = self._split_by_pauses(cleaned)
        pieces: List[str] = []
        for p in paragraphs:
            pieces.extend(self._split_long_text(p, max_tokens))

        blocks: List[UniversalBlock] = []
        current_parts: List[str] = []
        current_tokens = 0
        chunk_index = 0

        for piece in pieces:
            piece_tokens = count_tokens(piece)
            if current_parts and current_tokens + piece_tokens > max_tokens:
                if current_tokens >= min_tokens:
                    block_text = clean_text("\n\n".join(current_parts))
                    blocks.append(
                        self._make_block(block_text, author, source_title, source_id, chunk_index)
                    )
                    chunk_index += 1
                    current_parts = []
                    current_tokens = 0

            current_parts.append(piece)
            current_tokens += piece_tokens

        if current_parts:
            block_text = clean_text("\n\n".join(current_parts))
            blocks.append(self._make_block(block_text, author, source_title, source_id, chunk_index))

        for i, b in enumerate(blocks):
            b.chunk_index = i
            b.total_chunks = len(blocks)

        return blocks

    def _make_block(
        self, text: str, author: str, source_title: str, source_id: str, chunk_index: int
    ) -> UniversalBlock:
        title = self._make_title(text)
        return UniversalBlock(
            text=text,
            title=title,
            summary="",
            author=author,
            source_title=source_title,
            source_type="youtube",
            source_id=source_id,
            chunk_index=chunk_index,
        )

    def _extract_youtube_config(self, config: dict) -> dict:
        if "chunking" in config and isinstance(config.get("chunking"), dict):
            return config["chunking"].get("youtube", {})
        return config

    def _split_by_pauses(self, text: str) -> List[str]:
        parts: List[str] = []
        for part in re.split(r"\n\n+|\.\.\.\s+", text):
            part = part.strip()
            if part:
                parts.append(part)
        if not parts:
            return split_into_paragraphs(text)
        return parts

    def _split_long_text(self, text: str, max_tokens: int) -> List[str]:
        if count_tokens(text) <= max_tokens:
            return [text]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        parts: List[str] = []
        current = []
        current_tokens = 0
        for s in sentences:
            if not s:
                continue
            s_tokens = count_tokens(s)
            if current and current_tokens + s_tokens > max_tokens:
                parts.append(" ".join(current))
                current = []
                current_tokens = 0
            if s_tokens > max_tokens:
                parts.extend(self._split_by_words(s, max_tokens))
            else:
                current.append(s)
                current_tokens += s_tokens
        if current:
            parts.append(" ".join(current))
        return parts

    def _split_by_words(self, text: str, max_tokens: int) -> List[str]:
        words = text.split()
        parts: List[str] = []
        current = []
        current_tokens = 0
        for w in words:
            w_tokens = count_tokens(w)
            if current and current_tokens + w_tokens > max_tokens:
                parts.append(" ".join(current))
                current = []
                current_tokens = 0
            current.append(w)
            current_tokens += w_tokens
        if current:
            parts.append(" ".join(current))
        return parts

    def _make_title(self, text: str) -> str:
        words = re.findall(r"[\w'-]+", text)
        if not words:
            return ""
        return " ".join(words[:10])
