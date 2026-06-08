"""Contracts for contextual retrieval query composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION = "contextual_retrieval_query_composer_v1"


@dataclass
class RetrievalQueryComposerPayload:
    """Stable trace payload for the deterministic retrieval query composer."""

    enabled: bool = True
    mode: str = "deterministic_v1"
    retrieval_need: str = "none"
    retrieval_action: str = "suppress_rag"
    query_source: str = "current_user_message"
    composed_query: str = ""
    query_terms: list[str] = field(default_factory=list)
    inherited_topic: str = ""
    inherited_offer_type: str = ""
    confidence: float = 0.0
    writer_can_ignore_rag: bool = True
    include_for_writer_if_found: bool = False
    max_chunks_for_writer: int = 0
    max_chars_per_chunk: int = 0
    suppress_reason: str = ""
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    no_user_facing_text_created: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION,
            "enabled": bool(self.enabled),
            "mode": self.mode,
            "retrieval_need": self.retrieval_need,
            "retrieval_action": self.retrieval_action,
            "query_source": self.query_source,
            "composed_query": self.composed_query,
            "query_terms": list(self.query_terms),
            "inherited_topic": self.inherited_topic,
            "inherited_offer_type": self.inherited_offer_type,
            "confidence": float(self.confidence),
            "writer_can_ignore_rag": bool(self.writer_can_ignore_rag),
            "include_for_writer_if_found": bool(self.include_for_writer_if_found),
            "max_chunks_for_writer": int(self.max_chunks_for_writer),
            "max_chars_per_chunk": int(self.max_chars_per_chunk),
            "suppress_reason": self.suppress_reason,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "no_user_facing_text_created": True,
        }


__all__ = [
    "CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION",
    "RetrievalQueryComposerPayload",
]
