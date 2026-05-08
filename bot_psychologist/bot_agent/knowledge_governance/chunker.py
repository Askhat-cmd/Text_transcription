"""Deterministic markdown chunker for governed knowledge units."""

from __future__ import annotations

import hashlib
import re

from .classifiers import classify_chunk_governance_v1
from .contracts import GovernedKnowledgeChunk, KnowledgeSourceManifest


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().split())


def _build_summary(text: str, max_chars: int = 260) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""
    match = re.search(r"(.{30,260}?[.!?])(?:\s|$)", normalized)
    if match:
        return match.group(1).strip()
    return normalized[:max_chars].rstrip()


def _heading_level(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _split_section_text(
    *,
    section_title: str,
    text: str,
    max_chars: int,
    soft_min_chars: int,
) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    is_practice = any(marker in section_title.lower() for marker in ("практик", "exercise", "упражн"))
    practice_soft_limit = int(max_chars * 1.35)
    if is_practice and len(cleaned) <= practice_soft_limit:
        return [cleaned]
    if len(cleaned) <= max_chars:
        return [cleaned]

    parts = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    chunks: list[str] = []
    current = ""

    for part in parts:
        if len(part) > max_chars:
            sentence_parts = re.split(r"(?<=[.!?])\s+", part)
            for sent in sentence_parts:
                sent = sent.strip()
                if not sent:
                    continue
                candidate = f"{current}\n\n{sent}".strip() if current else sent
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    current = sent
            continue

        candidate = f"{current}\n\n{part}".strip() if current else part
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if len(current) >= soft_min_chars or not current:
            if current:
                chunks.append(current)
            current = part
        else:
            chunks.append(candidate[:max_chars].rstrip())
            current = ""

    if current:
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def chunk_markdown_document_v1(
    *,
    text: str,
    manifest: KnowledgeSourceManifest,
    max_chars: int = 1800,
    soft_min_chars: int = 400,
) -> list[GovernedKnowledgeChunk]:
    """Chunk markdown by heading hierarchy and classify each chunk."""
    lines = (text or "").splitlines()
    sections: list[dict[str, object]] = []
    heading_stack: list[str] = []
    buffer: list[str] = []
    section_title = manifest.title or manifest.source_id
    section_index = 0

    def flush_buffer() -> None:
        nonlocal section_index
        body = "\n".join(buffer).strip()
        if not body:
            return
        sections.append(
            {
                "index": section_index,
                "title": section_title,
                "heading_path": list(heading_stack) if heading_stack else [section_title],
                "text": body,
            }
        )
        section_index += 1

    for line in lines:
        heading = _heading_level(line)
        if heading is None:
            buffer.append(line)
            continue

        flush_buffer()
        buffer = []
        level, heading_text = heading
        while len(heading_stack) >= level:
            heading_stack.pop()
        heading_stack.append(heading_text)
        section_title = heading_text

    flush_buffer()

    chunks: list[GovernedKnowledgeChunk] = []
    chunk_counter = 1

    for section in sections:
        heading_path = [str(item) for item in section["heading_path"]]
        title = str(section["title"])
        section_text = str(section["text"])
        section_parts = _split_section_text(
            section_title=title,
            text=section_text,
            max_chars=max_chars,
            soft_min_chars=soft_min_chars,
        )
        for part_index, part_text in enumerate(section_parts):
            normalized = _normalize(part_text)
            short_hash = hashlib.sha1(
                f"{manifest.source_id}|{heading_path}|{normalized}".encode("utf-8")
            ).hexdigest()[:8]
            chunk_id = f"{manifest.source_id}::chunk::{chunk_counter:04d}::{short_hash}"
            classification = classify_chunk_governance_v1(
                chunk_text=part_text,
                heading_path=heading_path,
                manifest=manifest,
            )
            chunks.append(
                GovernedKnowledgeChunk(
                    chunk_id=chunk_id,
                    source_id=manifest.source_id,
                    source_title=manifest.title,
                    chunk_index=chunk_counter,
                    heading_path=heading_path,
                    title=title,
                    text=part_text,
                    summary=_build_summary(part_text),
                    chunk_type=str(classification.get("chunk_type", "theory")),
                    allowed_use=list(classification.get("allowed_use", [])),
                    safety_flags=list(classification.get("safety_flags", [])),
                    tags=list(classification.get("tags", [])),
                    lens_family=list(classification.get("lens_family", [])),
                    practice_metadata=dict(classification.get("practice_metadata", {})),
                    governance_notes=list(classification.get("governance_notes", [])),
                    source_trace={
                        "chunker_version": "chunk_markdown_document_v1",
                        "section_index": int(section["index"]),
                        "section_part_index": part_index,
                        "source_kind": manifest.source_kind,
                        "language": manifest.language,
                    },
                )
            )
            chunk_counter += 1

    return chunks
