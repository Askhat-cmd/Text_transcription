"""Contracts for PRD-047.15-HF2-R1 hybrid retrieval planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


HYBRID_RETRIEVAL_PLANNER_VERSION = "hybrid_retrieval_planner_v1_r1"

ALLOWED_RETRIEVAL_ACTIONS = {
    "suppress_rag",
    "use_current_context_only",
    "query_kb",
    "query_memory",
    "query_kb_and_memory",
    "trace_only",
}
ALLOWED_PLANNER_MODES = {"off", "shadow", "apply"}
ALLOWED_CHUNK_TYPES = {
    "concept",
    "mechanism",
    "dialogue_move",
    "practice",
    "safety",
    "diagnostic_lens",
    "source_fragment",
    "general_text",
}


def normalize_chunk_type(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_CHUNK_TYPES else "general_text"


@dataclass
class HybridRetrievalPlan:
    """Strict metadata-only retrieval plan."""

    retrieval_needed: bool = False
    retrieval_action: str = "trace_only"
    composed_query: str = ""
    needed_chunk_types: list[str] = field(default_factory=list)
    avoided_chunk_types: list[str] = field(default_factory=list)
    mechanism_hints: list[str] = field(default_factory=list)
    depth_level_hint: int = 0
    safety_layer_required: bool = False
    allowed_use_filter_hint: list[str] = field(default_factory=lambda: ["writer_support"])
    diagnostic_hints_used: bool = False
    writer_can_ignore_rag: bool = True
    retrieval_gap_reason: str = ""
    no_user_facing_text_created: bool = True
    fallback_if_invalid: str = "legacy_query"
    constraints_for_writer: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "retrieval_needed": bool(self.retrieval_needed),
            "retrieval_action": str(self.retrieval_action or "trace_only"),
            "composed_query": str(self.composed_query or ""),
            "needed_chunk_types": [normalize_chunk_type(item) for item in list(self.needed_chunk_types or [])],
            "avoided_chunk_types": [normalize_chunk_type(item) for item in list(self.avoided_chunk_types or [])],
            "mechanism_hints": [str(item) for item in list(self.mechanism_hints or []) if str(item).strip()],
            "depth_level_hint": max(0, min(int(self.depth_level_hint or 0), 3)),
            "safety_layer_required": bool(self.safety_layer_required),
            "allowed_use_filter_hint": [
                str(item) for item in list(self.allowed_use_filter_hint or []) if str(item).strip()
            ] or ["writer_support"],
            "diagnostic_hints_used": bool(self.diagnostic_hints_used),
            "writer_can_ignore_rag": bool(self.writer_can_ignore_rag),
            "retrieval_gap_reason": str(self.retrieval_gap_reason or ""),
            "no_user_facing_text_created": bool(self.no_user_facing_text_created),
            "fallback_if_invalid": str(self.fallback_if_invalid or "legacy_query"),
            "constraints_for_writer": [
                str(item) for item in list(self.constraints_for_writer or []) if str(item).strip()
            ],
            "confidence": max(0.0, min(float(self.confidence or 0.0), 1.0)),
        }


__all__ = [
    "ALLOWED_CHUNK_TYPES",
    "ALLOWED_PLANNER_MODES",
    "ALLOWED_RETRIEVAL_ACTIONS",
    "HYBRID_RETRIEVAL_PLANNER_VERSION",
    "HybridRetrievalPlan",
    "normalize_chunk_type",
]
