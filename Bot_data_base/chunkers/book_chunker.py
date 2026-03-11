from __future__ import annotations

import os
import re
from typing import List, Tuple

from models.universal_block import UniversalBlock
from utils.text_utils import count_tokens, clean_text, split_into_paragraphs


class BookChunker:
    def __init__(self, config: dict):
        self.config = config or {}
        self._book_cfg = self._extract_book_config(self.config)

    def chunk_file(
        self,
        file_path: str,
        author: str,
        book_title: str,
        language: str = "ru",
        author_id: str = "",
    ) -> List[UniversalBlock]:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return self.chunk_file_from_text(text, author, book_title, language, author_id)

    def chunk_file_from_text(
        self,
        text: str,
        author: str,
        book_title: str,
        language: str = "ru",
        author_id: str = "",
    ) -> List[UniversalBlock]:
        cleaned = clean_text(text)
        chapters = self._parse_chapters(cleaned)
        if not chapters:
            chapters = [("Chapter 1", cleaned)]

        blocks: List[UniversalBlock] = []
        chunk_index = 0
        for i, (chapter_title, chapter_text) in enumerate(chapters):
            chapter_blocks = self._chunk_chapter(
                chapter_text=chapter_text,
                chapter_title=chapter_title,
                chapter_index=i,
                start_chunk_index=chunk_index,
                author=author,
                author_id=author_id,
                book_title=book_title,
                language=language,
            )
            blocks.extend(chapter_blocks)
            chunk_index = len(blocks)

        for b in blocks:
            b.total_chunks = len(blocks)
        return blocks

    def _parse_chapters(self, text: str) -> List[Tuple[str, str]]:
        if not text:
            return []

        lines = text.split("\n")
        header_indices = []
        for idx, line in enumerate(lines):
            if self._is_header_line(line):
                header_indices.append(idx)

        if not header_indices:
            return []

        chapters: List[Tuple[str, str]] = []
        for i, start_idx in enumerate(header_indices):
            end_idx = header_indices[i + 1] if i + 1 < len(header_indices) else len(lines)
            title_line = lines[start_idx].strip()
            title = self._clean_header_title(title_line)
            body_lines = lines[start_idx + 1 : end_idx]
            chapter_text = clean_text("\n".join(body_lines))
            chapters.append((title, chapter_text))

        return chapters

    def _chunk_chapter(
        self,
        chapter_text: str,
        chapter_title: str,
        chapter_index: int,
        start_chunk_index: int,
        author: str,
        author_id: str,
        book_title: str,
        language: str,
    ) -> List[UniversalBlock]:
        target_tokens = int(self._book_cfg.get("target_tokens", 1000))
        min_tokens = int(self._book_cfg.get("min_tokens", 400))
        max_tokens = int(self._book_cfg.get("max_tokens", 1400))
        overlap_tokens = int(self._book_cfg.get("overlap_tokens", 150))

        paragraphs = split_into_paragraphs(chapter_text)
        pieces: List[str] = []
        for p in paragraphs:
            pieces.extend(self._split_long_text(p, max_tokens))

        blocks: List[UniversalBlock] = []
        current_parts: List[str] = []
        current_tokens = 0
        overlap_text = ""
        chunk_index = start_chunk_index

        for piece in pieces:
            piece_tokens = count_tokens(piece)

            if not current_parts and overlap_text:
                current_parts.append(overlap_text)
                current_tokens = count_tokens(overlap_text)
                overlap_text = ""

            if current_parts and current_tokens + piece_tokens > max_tokens:
                if current_tokens >= min_tokens or current_tokens >= target_tokens:
                    block_text = clean_text("\n\n".join(current_parts))
                    blocks.append(
                        self._make_block(
                            block_text,
                            chapter_title,
                            chapter_index,
                            chunk_index,
                            author,
                            author_id,
                            book_title,
                            language,
                        )
                    )
                    chunk_index += 1
                    overlap_text = self._take_last_tokens(block_text, overlap_tokens)
                    current_parts = []
                    current_tokens = 0

            current_parts.append(piece)
            current_tokens += piece_tokens

        if current_parts:
            block_text = clean_text("\n\n".join(current_parts))
            blocks.append(
                self._make_block(
                    block_text,
                    chapter_title,
                    chapter_index,
                    chunk_index,
                    author,
                    author_id,
                    book_title,
                    language,
                )
            )

        return blocks

    def _make_block(
        self,
        text: str,
        chapter_title: str,
        chapter_index: int,
        chunk_index: int,
        author: str,
        author_id: str,
        book_title: str,
        language: str,
    ) -> UniversalBlock:
        source_author_id = author_id or self._slugify(author)
        source_book_id = self._slugify(book_title)
        source_id = f"{source_author_id}__{source_book_id}" if source_author_id else source_book_id
        return UniversalBlock(
            text=text,
            title=chapter_title,
            summary="",
            author=author,
            author_id=author_id,
            source_title=book_title,
            source_type="book",
            source_id=source_id,
            language=language,
            chapter_title=chapter_title,
            chapter_index=chapter_index,
            chunk_index=chunk_index,
        )

    def _extract_book_config(self, config: dict) -> dict:
        if "chunking" in config and isinstance(config.get("chunking"), dict):
            return config["chunking"].get("book", {})
        return config

    def _is_header_line(self, line: str) -> bool:
        text = line.strip()
        if not text:
            return False
        patterns = [
            r"^#{1,3}\s+.+$",
            r"^(Глава|Chapter|ГЛАВА|CHAPTER)\s+[\dIVXivx]+.*$",
            r"^\d+\.\s+[А-ЯA-Z].{5,}$",
            r"^[А-ЯA-Z\s]{10,}$",
        ]
        return any(re.match(p, text) for p in patterns)

    def _clean_header_title(self, line: str) -> str:
        title = line.strip()
        title = re.sub(r"^#{1,3}\s+", "", title)
        return title.strip()

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

    def _take_last_tokens(self, text: str, n_tokens: int) -> str:
        if n_tokens <= 0 or not text:
            return ""
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode(text)
            if len(tokens) <= n_tokens:
                return text
            return enc.decode(tokens[-n_tokens:])
        except Exception:
            words = text.split()
            return " ".join(words[-n_tokens:])

    def _slugify(self, value: str) -> str:
        if not value:
            return ""
        value = value.strip().lower()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"[^0-9a-zа-я_]+", "", value)
        return value
