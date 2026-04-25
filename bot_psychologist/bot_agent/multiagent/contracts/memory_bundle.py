"""Memory bundle contract for Writer integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryBundle:
    """Prepared memory payload for Writer layer."""

    conversation_context: str = ""
    semantic_hits: list[str] = field(default_factory=list)
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_context": self.conversation_context,
            "semantic_hits": self.semantic_hits,
            "retrieved_chunks": self.retrieved_chunks,
            "diagnostics": self.diagnostics,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryBundle":
        return cls(
            conversation_context=str(payload.get("conversation_context", "")),
            semantic_hits=list(payload.get("semantic_hits", [])),
            retrieved_chunks=list(payload.get("retrieved_chunks", [])),
            diagnostics=dict(payload.get("diagnostics", {})),
        )

