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
    governance: dict[str, Any] = field(default_factory=dict)
    chunking_quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source": self.source,
            "score": float(self.score),
            "governance": dict(self.governance or {}),
            "chunking_quality": dict(self.chunking_quality or {}),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SemanticHit":
        return cls(
            chunk_id=str(payload.get("chunk_id", "")),
            content=str(payload.get("content", "")),
            source=str(payload.get("source", "unknown")),
            score=float(payload.get("score", 0.0) or 0.0),
            governance=(
                dict(payload.get("governance", {}))
                if isinstance(payload.get("governance"), dict)
                else {}
            ),
            chunking_quality=(
                dict(payload.get("chunking_quality", {}))
                if isinstance(payload.get("chunking_quality"), dict)
                else {}
            ),
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
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    personal_history_context: list[dict[str, Any]] = field(default_factory=list)
    semantic_memory_hits: list[dict[str, Any]] = field(default_factory=list)
    knowledge_rag_hits: list[dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: list[Any] = field(default_factory=list)
    has_relevant_knowledge: bool = False
    context_turns: int = 0
    knowledge_policy_trace: dict[str, Any] = field(default_factory=dict)
    rag_retrieval_trace: dict[str, Any] = field(default_factory=dict)
    hybrid_retrieval_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_context": self.conversation_context,
            "rag_query": self.rag_query,
            "user_profile": self.user_profile.to_dict(),
            "semantic_hits": [hit.to_dict() for hit in self.semantic_hits],
            "recent_turns": list(self.recent_turns),
            "personal_history_context": list(self.personal_history_context),
            "semantic_memory_hits": list(self.semantic_memory_hits),
            "knowledge_rag_hits": list(self.knowledge_rag_hits),
            "retrieved_chunks": self.retrieved_chunks,
            "has_relevant_knowledge": bool(self.has_relevant_knowledge),
            "context_turns": int(self.context_turns),
            "knowledge_policy_trace": dict(self.knowledge_policy_trace or {}),
            "rag_retrieval_trace": dict(self.rag_retrieval_trace or {}),
            "hybrid_retrieval_trace": dict(self.hybrid_retrieval_trace or {}),
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
            recent_turns=list(payload.get("recent_turns", [])),
            personal_history_context=list(payload.get("personal_history_context", [])),
            semantic_memory_hits=list(payload.get("semantic_memory_hits", [])),
            knowledge_rag_hits=list(payload.get("knowledge_rag_hits", [])),
            retrieved_chunks=list(payload.get("retrieved_chunks", [])),
            has_relevant_knowledge=bool(payload.get("has_relevant_knowledge", False)),
            context_turns=int(payload.get("context_turns", 0) or 0),
            knowledge_policy_trace=(
                dict(payload.get("knowledge_policy_trace", {}))
                if isinstance(payload.get("knowledge_policy_trace"), dict)
                else {}
            ),
            rag_retrieval_trace=(
                dict(payload.get("rag_retrieval_trace", {}))
                if isinstance(payload.get("rag_retrieval_trace"), dict)
                else {}
            ),
            hybrid_retrieval_trace=(
                dict(payload.get("hybrid_retrieval_trace", {}))
                if isinstance(payload.get("hybrid_retrieval_trace"), dict)
                else {}
            ),
        )
