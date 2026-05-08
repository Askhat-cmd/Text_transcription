from __future__ import annotations

import hashlib
import re
from typing import List, Tuple

from chunkers.structure_parser import StructuredSection, parse_markdown_like_sections_v1
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

        structured_blocks = self._chunk_with_structure(
            cleaned,
            author=author,
            author_id=author_id,
            book_title=book_title,
            language=language,
        )
        if structured_blocks is not None:
            for block in structured_blocks:
                block.total_chunks = len(structured_blocks)
            return structured_blocks

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

    def _chunk_with_structure(
        self,
        cleaned_text: str,
        *,
        author: str,
        author_id: str,
        book_title: str,
        language: str,
    ) -> List[UniversalBlock] | None:
        if not cleaned_text:
            return []

        try:
            sections = parse_markdown_like_sections_v1(cleaned_text)
        except Exception:
            return None

        if not self._should_use_structure(sections):
            return None

        max_tokens = int(self._book_cfg.get("max_tokens", 1400))
        min_tokens = int(self._book_cfg.get("min_tokens", 400))
        target_tokens = int(self._book_cfg.get("target_tokens", 1000))
        overlap_tokens = int(self._book_cfg.get("overlap_tokens", 150))

        source_author_id = author_id or self._slugify(author)
        source_book_id = self._slugify(book_title)
        source_id = f"{source_author_id}__{source_book_id}" if source_author_id else source_book_id

        blocks: List[UniversalBlock] = []
        chunk_index = 0

        for section_idx, section in enumerate(sections):
            section_text = clean_text(section.text)
            if not section_text:
                continue

            section_role = (section.section_role_hint or "unknown").strip().lower()
            parent_section_id = self._build_parent_section_id(
                source_id=source_id,
                section_index=section_idx,
                title=section.title,
                start_line=section.start_line,
            )

            split_payload = self._split_section_role_aware(
                section_text=section_text,
                section_role=section_role,
                max_tokens=max_tokens,
                min_tokens=min_tokens,
                target_tokens=target_tokens,
                overlap_tokens=overlap_tokens,
            )

            chapter_title = section.heading_path[0] if section.heading_path else section.title
            for chunk_text, split_reason in split_payload:
                blocks.append(
                    self._make_block(
                        text=chunk_text,
                        chapter_title=chapter_title,
                        chapter_index=section_idx,
                        chunk_index=chunk_index,
                        author=author,
                        author_id=author_id,
                        book_title=book_title,
                        language=language,
                        title_override=section.title,
                        heading_path=section.heading_path,
                        section_role_hint=section_role,
                        boundary_confidence=section.boundary_confidence,
                        split_reason=split_reason,
                        parent_section_id=parent_section_id,
                    )
                )
                chunk_index += 1

        return blocks if blocks else None

    def _should_use_structure(self, sections: List[StructuredSection]) -> bool:
        if len(sections) >= 2:
            return True
        if len(sections) == 1:
            role = (sections[0].section_role_hint or "").strip().lower()
            return role in {"practice", "safety", "lens", "architecture", "case", "quote"}
        return False

    def _split_section_role_aware(
        self,
        *,
        section_text: str,
        section_role: str,
        max_tokens: int,
        min_tokens: int,
        target_tokens: int,
        overlap_tokens: int,
    ) -> list[tuple[str, str]]:
        role = (section_role or "unknown").lower()

        if role == "practice":
            return self._split_practice_section(
                section_text=section_text,
                max_tokens=max_tokens,
                min_tokens=min_tokens,
            )

        if role == "safety":
            if count_tokens(section_text) <= max_tokens:
                return [(section_text, "safety_boundary")]
            parts = self._chunk_text_budget(section_text, target_tokens, min_tokens, max_tokens, 0)
            return [(part, "safety_boundary_split") for part in parts]

        if role == "lens":
            if count_tokens(section_text) <= max_tokens:
                return [(section_text, "lens_boundary")]
            parts = self._chunk_text_budget(section_text, target_tokens, min_tokens, max_tokens, overlap_tokens)
            return [(part, "lens_boundary_split") for part in parts]

        if role == "architecture":
            if count_tokens(section_text) <= max_tokens:
                return [(section_text, "architecture_boundary")]
            parts = self._chunk_text_budget(section_text, target_tokens, min_tokens, max_tokens, overlap_tokens)
            return [(part, "architecture_boundary_split") for part in parts]

        parts = self._chunk_text_budget(section_text, target_tokens, min_tokens, max_tokens, overlap_tokens)
        return [(part, "theory_budget_split") for part in parts]

    def _split_practice_section(
        self,
        *,
        section_text: str,
        max_tokens: int,
        min_tokens: int,
    ) -> list[tuple[str, str]]:
        if count_tokens(section_text) <= max_tokens:
            return [(section_text, "practice_preserved")]

        parts = self._split_practice_steps(section_text)
        normalized_parts: list[str] = []
        for part in parts:
            if count_tokens(part) > max_tokens:
                normalized_parts.extend(self._split_long_text(part, max_tokens))
            elif part.strip():
                normalized_parts.append(part.strip())

        if not normalized_parts:
            fallback_parts = self._chunk_text_budget(section_text, max_tokens, min_tokens, max_tokens, 0)
            return [(part, "practice_step_split") for part in fallback_parts]

        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for part in normalized_parts:
            piece_tokens = count_tokens(part)
            if current and current_tokens + piece_tokens > max_tokens:
                chunks.append(clean_text("\n\n".join(current)))
                current = []
                current_tokens = 0
            current.append(part)
            current_tokens += piece_tokens

        if current:
            chunks.append(clean_text("\n\n".join(current)))

        if len(chunks) == 1:
            return [(chunks[0], "practice_preserved")]

        return [(chunk, "practice_step_split") for chunk in chunks if chunk]

    def _split_practice_steps(self, section_text: str) -> list[str]:
        paragraphs = split_into_paragraphs(section_text)
        if not paragraphs:
            return [section_text]

        step_start = re.compile(r"^(?:шаг\s*\d+|step\s*\d+|\d+[\).]|[-*•])\s*", re.IGNORECASE)
        groups: list[list[str]] = []
        current: list[str] = []

        for paragraph in paragraphs:
            p = paragraph.strip()
            if not p:
                continue
            is_step = bool(step_start.match(p))
            if is_step and current:
                groups.append(current)
                current = [p]
                continue
            current.append(p)

        if current:
            groups.append(current)

        return [clean_text("\n\n".join(group)) for group in groups if group]

    def _chunk_text_budget(
        self,
        text: str,
        target_tokens: int,
        min_tokens: int,
        max_tokens: int,
        overlap_tokens: int,
    ) -> list[str]:
        paragraphs = split_into_paragraphs(text)
        pieces: List[str] = []
        for paragraph in paragraphs:
            pieces.extend(self._split_long_text(paragraph, max_tokens))

        blocks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0
        overlap_text = ""

        for piece in pieces:
            piece_tokens = count_tokens(piece)

            if not current_parts and overlap_text:
                current_parts.append(overlap_text)
                current_tokens = count_tokens(overlap_text)
                overlap_text = ""

            if current_parts and current_tokens + piece_tokens > max_tokens:
                if current_tokens >= min_tokens or current_tokens >= target_tokens:
                    block_text = clean_text("\n\n".join(current_parts))
                    blocks.append(block_text)
                    overlap_text = self._take_last_tokens(block_text, overlap_tokens)
                    current_parts = []
                    current_tokens = 0

            current_parts.append(piece)
            current_tokens += piece_tokens

        if current_parts:
            block_text = clean_text("\n\n".join(current_parts))
            blocks.append(block_text)

        return [block for block in blocks if block]

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

        pieces = self._chunk_text_budget(chapter_text, target_tokens, min_tokens, max_tokens, overlap_tokens)

        blocks: List[UniversalBlock] = []
        chunk_index = start_chunk_index
        for text_piece in pieces:
            blocks.append(
                self._make_block(
                    text_piece,
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
        title_override: str | None = None,
        heading_path: list[str] | None = None,
        section_role_hint: str = "",
        boundary_confidence: float = 0.0,
        split_reason: str = "",
        parent_section_id: str = "",
    ) -> UniversalBlock:
        source_author_id = author_id or self._slugify(author)
        source_book_id = self._slugify(book_title)
        source_id = f"{source_author_id}__{source_book_id}" if source_author_id else source_book_id
        return UniversalBlock(
            text=text,
            title=(title_override or chapter_title),
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
            heading_path=heading_path or [],
            section_role_hint=section_role_hint,
            boundary_confidence=float(boundary_confidence or 0.0),
            split_reason=split_reason,
            parent_section_id=parent_section_id,
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
        for sentence in sentences:
            if not sentence:
                continue
            sentence_tokens = count_tokens(sentence)
            if current and current_tokens + sentence_tokens > max_tokens:
                parts.append(" ".join(current))
                current = []
                current_tokens = 0
            if sentence_tokens > max_tokens:
                parts.extend(self._split_by_words(sentence, max_tokens))
            else:
                current.append(sentence)
                current_tokens += sentence_tokens
        if current:
            parts.append(" ".join(current))
        return parts

    def _split_by_words(self, text: str, max_tokens: int) -> List[str]:
        words = text.split()
        parts: List[str] = []
        current = []
        current_tokens = 0
        for word in words:
            word_tokens = count_tokens(word)
            if current and current_tokens + word_tokens > max_tokens:
                parts.append(" ".join(current))
                current = []
                current_tokens = 0
            current.append(word)
            current_tokens += word_tokens
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

    def _build_parent_section_id(
        self,
        *,
        source_id: str,
        section_index: int,
        title: str,
        start_line: int,
    ) -> str:
        payload = f"{source_id}|{section_index}|{title}|{start_line}"
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
        return f"{source_id}::section::{section_index}::{digest}"
