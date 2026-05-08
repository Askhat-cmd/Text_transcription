"""Export governed chunks to DB_JSON-compatible preview payload."""

from __future__ import annotations

from typing import Any

from .contracts import GovernedKnowledgeChunk, KnowledgeSourceManifest


def _complexity_by_type(chunk_type: str) -> float:
    mapping = {
        "safety": 0.7,
        "protocol": 0.65,
        "practice": 0.55,
        "principle": 0.6,
        "lens": 0.7,
        "style": 0.45,
        "theory": 0.65,
        "case": 0.5,
        "quote": 0.35,
        "excluded": 0.9,
    }
    return float(mapping.get(chunk_type, 0.6))


def export_governed_chunks_to_db_json_v1(
    *,
    chunks: list[GovernedKnowledgeChunk],
    manifest: KnowledgeSourceManifest,
) -> dict[str, Any]:
    """Produce DB_JSON-like payload with nested governance metadata."""
    blocks: list[dict[str, Any]] = []
    for chunk in chunks:
        blocks.append(
            {
                "id": chunk.chunk_id,
                "title": chunk.title,
                "summary": chunk.summary,
                "text": chunk.text,
                "complexity": _complexity_by_type(chunk.chunk_type),
                "metadata": {
                    "source_title": manifest.title,
                    "source_type": manifest.source_kind,
                    "author": manifest.author or "",
                    "author_id": manifest.source_id,
                    "chunk_index": int(chunk.chunk_index),
                    "language": manifest.language or "ru",
                    "heading_path": list(chunk.heading_path),
                    "governance": {
                        "chunk_type": chunk.chunk_type,
                        "allowed_use": list(chunk.allowed_use),
                        "safety_flags": list(chunk.safety_flags),
                        "lens_family": list(chunk.lens_family),
                        "tags": list(chunk.tags),
                        "practice_metadata": dict(chunk.practice_metadata),
                        "governance_notes": list(chunk.governance_notes),
                        "source_trace": dict(chunk.source_trace),
                    },
                },
            }
        )

    return {
        "schema_version": "governed_kb_v1",
        "source_id": manifest.source_id,
        "source_type": manifest.source_kind,
        "title": manifest.title,
        "version": manifest.version,
        "blocks": blocks,
    }
