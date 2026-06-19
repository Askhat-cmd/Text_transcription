"""Semantic chunk card contract for the PRD-047.27 pilot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SEMANTIC_CHUNK_CARD_SCHEMA_VERSION = "semantic_chunk_card_v1"

CHUNK_TYPES = {
    "concept",
    "mechanism",
    "practice",
    "diagnostic_lens",
    "dialogue_move",
    "anti_pattern",
    "safety",
    "source_fragment",
}
ALLOWED_USE_VALUES = {"direct_to_writer", "internal_lens", "writer_support"}
QUOTE_POLICIES = {"paraphrase_only", "can_quote_short", "internal_only", "do_not_use"}
PRACTICE_POLICIES = {
    "no_practice_unless_requested",
    "practice_allowed_if_explicit",
    "not_a_practice",
}


@dataclass(frozen=True)
class SemanticChunkCard:
    card_id: str
    schema_version: str
    title: str
    chunk_type: str
    source_ref: dict[str, Any]
    core_thesis: str
    mechanism_hints: list[str]
    user_markers_examples: list[str]
    allowed_use: list[str]
    avoid_when: list[str]
    depth_level: int
    quote_policy: str
    practice_policy: str
    writer_instruction: str
    safety_notes: list[str] = field(default_factory=list)
    writer_can_ignore: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticChunkCard":
        return cls(
            card_id=str(payload.get("card_id", "") or "").strip(),
            schema_version=str(payload.get("schema_version", "") or "").strip(),
            title=str(payload.get("title", "") or "").strip(),
            chunk_type=str(payload.get("chunk_type", "") or "").strip(),
            source_ref=dict(payload.get("source_ref", {}) or {}),
            core_thesis=str(payload.get("core_thesis", "") or "").strip(),
            mechanism_hints=_string_list(payload.get("mechanism_hints")),
            user_markers_examples=_string_list(payload.get("user_markers_examples")),
            allowed_use=_string_list(payload.get("allowed_use")),
            avoid_when=_string_list(payload.get("avoid_when")),
            depth_level=int(payload.get("depth_level", 0) or 0),
            quote_policy=str(payload.get("quote_policy", "") or "").strip(),
            practice_policy=str(payload.get("practice_policy", "") or "").strip(),
            writer_instruction=str(payload.get("writer_instruction", "") or "").strip(),
            safety_notes=_string_list(payload.get("safety_notes")),
            writer_can_ignore=bool(payload.get("writer_can_ignore", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "schema_version": self.schema_version,
            "title": self.title,
            "chunk_type": self.chunk_type,
            "source_ref": dict(self.source_ref),
            "core_thesis": self.core_thesis,
            "mechanism_hints": list(self.mechanism_hints),
            "user_markers_examples": list(self.user_markers_examples),
            "allowed_use": list(self.allowed_use),
            "avoid_when": list(self.avoid_when),
            "depth_level": self.depth_level,
            "quote_policy": self.quote_policy,
            "practice_policy": self.practice_policy,
            "writer_instruction": self.writer_instruction,
            "safety_notes": list(self.safety_notes),
            "writer_can_ignore": self.writer_can_ignore,
        }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def validate_semantic_card_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    card = SemanticChunkCard.from_dict(payload)
    required_strings = {
        "card_id": card.card_id,
        "schema_version": card.schema_version,
        "title": card.title,
        "chunk_type": card.chunk_type,
        "core_thesis": card.core_thesis,
        "quote_policy": card.quote_policy,
        "practice_policy": card.practice_policy,
        "writer_instruction": card.writer_instruction,
    }
    for key, value in required_strings.items():
        if not value:
            errors.append(f"missing_required:{key}")
    if card.schema_version != SEMANTIC_CHUNK_CARD_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    if card.chunk_type not in CHUNK_TYPES:
        errors.append(f"invalid_chunk_type:{card.chunk_type}")
    if not card.allowed_use:
        errors.append("missing_allowed_use")
    for item in card.allowed_use:
        if item not in ALLOWED_USE_VALUES:
            errors.append(f"invalid_allowed_use:{item}")
    if card.quote_policy not in QUOTE_POLICIES:
        errors.append(f"invalid_quote_policy:{card.quote_policy}")
    if card.practice_policy not in PRACTICE_POLICIES:
        errors.append(f"invalid_practice_policy:{card.practice_policy}")
    if card.writer_can_ignore is not True:
        errors.append("writer_can_ignore_must_be_true")
    if card.depth_level < 0 or card.depth_level > 3:
        errors.append("invalid_depth_level")
    if card.chunk_type == "practice" and card.practice_policy != "practice_allowed_if_explicit":
        errors.append("practice_card_requires_explicit_policy")
    if card.practice_policy == "practice_allowed_if_explicit" and "user_asked_no_practice" not in card.avoid_when:
        errors.append("practice_card_missing_no_practice_avoidance")
    if not isinstance(card.source_ref, dict) or not str(card.source_ref.get("source_doc", "")).strip():
        errors.append("missing_source_ref_source_doc")
    return errors


__all__ = [
    "ALLOWED_USE_VALUES",
    "CHUNK_TYPES",
    "PRACTICE_POLICIES",
    "QUOTE_POLICIES",
    "SEMANTIC_CHUNK_CARD_SCHEMA_VERSION",
    "SemanticChunkCard",
    "validate_semantic_card_payload",
]

