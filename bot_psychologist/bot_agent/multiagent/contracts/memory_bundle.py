"""Memory bundle contract for Writer integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticHit:
    """One RAG hit item prepared for writer/runtime."""

    chunk_id: str
    content: str
    source: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source": self.source,
            "score": float(self.score),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticHit":
        return cls(
            chunk_id=str(payload.get("chunk_id", "")),
            content=str(payload.get("content", "")),
            source=str(payload.get("source", "unknown")),
            score=float(payload.get("score", 0.0) or 0.0),
        )


@dataclass
class UserProfile:
    """Long-term profile snapshot for user-aware responses."""

    patterns: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    progress_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patterns": list(self.patterns),
            "triggers": list(self.triggers),
            "values": list(self.values),
            "progress_notes": list(self.progress_notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UserProfile":
        return cls(
            patterns=[str(x) for x in payload.get("patterns", [])],
            triggers=[str(x) for x in payload.get("triggers", [])],
            values=[str(x) for x in payload.get("values", [])],
            progress_notes=[str(x) for x in payload.get("progress_notes", [])],
        )


@dataclass
class MemoryBundle:
    """Prepared memory payload for Writer layer."""

    conversation_context: str = ""
    rag_query: str = ""
    user_profile: UserProfile = field(default_factory=UserProfile)
    semantic_hits: list[SemanticHit] = field(default_factory=list)
    retrieved_chunks: list[Any] = field(default_factory=list)
    has_relevant_knowledge: bool = False
    context_turns: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_context": self.conversation_context,
            "rag_query": self.rag_query,
            "user_profile": self.user_profile.to_dict(),
            "semantic_hits": [hit.to_dict() for hit in self.semantic_hits],
            "retrieved_chunks": self.retrieved_chunks,
            "has_relevant_knowledge": bool(self.has_relevant_knowledge),
            "context_turns": int(self.context_turns),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryBundle":
        raw_profile = payload.get("user_profile", {})
        user_profile = (
            UserProfile.from_dict(raw_profile)
            if isinstance(raw_profile, dict)
            else UserProfile()
        )
        raw_hits = payload.get("semantic_hits", [])
        semantic_hits: list[SemanticHit] = []
        if isinstance(raw_hits, list):
            for item in raw_hits:
                if isinstance(item, SemanticHit):
                    semantic_hits.append(item)
                    continue
                if isinstance(item, dict):
                    semantic_hits.append(SemanticHit.from_dict(item))
                    continue
                semantic_hits.append(
                    SemanticHit(
                        chunk_id="",
                        content=str(item),
                        source="legacy",
                        score=0.0,
                    )
                )
        return cls(
            conversation_context=str(payload.get("conversation_context", "")),
            rag_query=str(payload.get("rag_query", "")),
            user_profile=user_profile,
            semantic_hits=semantic_hits,
            retrieved_chunks=list(payload.get("retrieved_chunks", [])),
            has_relevant_knowledge=bool(payload.get("has_relevant_knowledge", False)),
            context_turns=int(payload.get("context_turns", 0) or 0),
        )
