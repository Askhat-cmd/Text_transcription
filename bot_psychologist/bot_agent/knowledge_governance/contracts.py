"""Contracts for knowledge source governance and governed chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CHUNK_TYPE_VALUES = {
    "principle",
    "lens",
    "practice",
    "protocol",
    "safety",
    "style",
    "case",
    "quote",
    "theory",
    "excluded",
}

ALLOWED_USE_VALUES = {
    "internal_only",
    "writer_context",
    "diagnostic_lens",
    "practice_suggestion",
    "safety_protocol",
    "style_guidance",
    "do_not_use",
}

SAFETY_FLAG_VALUES = {
    "clinical_risk",
    "directive_risk",
    "spiritual_authority_risk",
    "too_strong_claim",
    "requires_grounding",
    "practice_requires_low_resource_check",
    "practice_requires_contraindication_note",
    "source_style_not_user_facing",
    "not_for_direct_quote",
}


def _dedupe_str_list(value: list[Any] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in value or []:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


@dataclass
class KnowledgeSourceManifest:
    source_id: str
    title: str
    source_kind: str
    author: str | None
    language: str
    version: str
    allowed_global_use: list[str] = field(default_factory=list)
    default_safety_flags: list[str] = field(default_factory=list)
    raw_path: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "source_kind": self.source_kind,
            "author": self.author,
            "language": self.language,
            "version": self.version,
            "allowed_global_use": list(self.allowed_global_use),
            "default_safety_flags": list(self.default_safety_flags),
            "raw_path": self.raw_path,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeSourceManifest":
        return cls(
            source_id=str(payload.get("source_id", "")),
            title=str(payload.get("title", "")),
            source_kind=str(payload.get("source_kind", "other")),
            author=(str(payload["author"]) if payload.get("author") is not None else None),
            language=str(payload.get("language", "ru")),
            version=str(payload.get("version", "unknown")),
            allowed_global_use=_dedupe_str_list(payload.get("allowed_global_use", [])),
            default_safety_flags=_dedupe_str_list(payload.get("default_safety_flags", [])),
            raw_path=(str(payload["raw_path"]) if payload.get("raw_path") is not None else None),
            notes=str(payload.get("notes", "")),
        )


@dataclass
class GovernedKnowledgeChunk:
    chunk_id: str
    source_id: str
    source_title: str
    chunk_index: int
    heading_path: list[str]
    title: str
    text: str
    summary: str
    chunk_type: str
    allowed_use: list[str]
    safety_flags: list[str]
    tags: list[str] = field(default_factory=list)
    lens_family: list[str] = field(default_factory=list)
    practice_metadata: dict[str, Any] = field(default_factory=dict)
    governance_notes: list[str] = field(default_factory=list)
    source_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "chunk_index": int(self.chunk_index),
            "heading_path": list(self.heading_path),
            "title": self.title,
            "text": self.text,
            "summary": self.summary,
            "chunk_type": self.chunk_type,
            "allowed_use": list(self.allowed_use),
            "safety_flags": list(self.safety_flags),
            "tags": list(self.tags),
            "lens_family": list(self.lens_family),
            "practice_metadata": dict(self.practice_metadata),
            "governance_notes": list(self.governance_notes),
            "source_trace": dict(self.source_trace),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GovernedKnowledgeChunk":
        heading_path_raw = payload.get("heading_path", [])
        return cls(
            chunk_id=str(payload.get("chunk_id", "")),
            source_id=str(payload.get("source_id", "")),
            source_title=str(payload.get("source_title", "")),
            chunk_index=int(payload.get("chunk_index", 0) or 0),
            heading_path=[str(item) for item in heading_path_raw] if isinstance(heading_path_raw, list) else [],
            title=str(payload.get("title", "")),
            text=str(payload.get("text", "")),
            summary=str(payload.get("summary", "")),
            chunk_type=str(payload.get("chunk_type", "theory")),
            allowed_use=_dedupe_str_list(payload.get("allowed_use", [])),
            safety_flags=_dedupe_str_list(payload.get("safety_flags", [])),
            tags=_dedupe_str_list(payload.get("tags", [])),
            lens_family=_dedupe_str_list(payload.get("lens_family", [])),
            practice_metadata=(
                dict(payload.get("practice_metadata", {}))
                if isinstance(payload.get("practice_metadata"), dict)
                else {}
            ),
            governance_notes=_dedupe_str_list(payload.get("governance_notes", [])),
            source_trace=(
                dict(payload.get("source_trace", {}))
                if isinstance(payload.get("source_trace"), dict)
                else {}
            ),
        )
