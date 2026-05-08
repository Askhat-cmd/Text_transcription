"""Context assembly contracts for Writer preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnContextItem:
    """One recent turn preserved in full form for writer context."""

    turn_id: str
    role: str
    content: str
    raw_chars: int
    source: str
    was_summarized: bool = False
    was_truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role,
            "content": self.content,
            "raw_chars": int(self.raw_chars),
            "source": self.source,
            "was_summarized": bool(self.was_summarized),
            "was_truncated": bool(self.was_truncated),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurnContextItem":
        return cls(
            turn_id=str(payload.get("turn_id", "")),
            role=str(payload.get("role", "")),
            content=str(payload.get("content", "")),
            raw_chars=int(payload.get("raw_chars", 0) or 0),
            source=str(payload.get("source", "recent_full")),
            was_summarized=bool(payload.get("was_summarized", False)),
            was_truncated=bool(payload.get("was_truncated", False)),
        )


@dataclass
class TurnMicroSummary:
    """Deterministic micro-summary of one long turn."""

    turn_id: str
    role: str
    summary: str
    important_quote: str | None
    raw_chars: int
    summary_chars: int
    was_truncated: bool
    summary_method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role,
            "summary": self.summary,
            "important_quote": self.important_quote,
            "raw_chars": int(self.raw_chars),
            "summary_chars": int(self.summary_chars),
            "was_truncated": bool(self.was_truncated),
            "summary_method": self.summary_method,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TurnMicroSummary":
        quote = payload.get("important_quote")
        return cls(
            turn_id=str(payload.get("turn_id", "")),
            role=str(payload.get("role", "")),
            summary=str(payload.get("summary", "")),
            important_quote=str(quote) if isinstance(quote, str) and quote.strip() else None,
            raw_chars=int(payload.get("raw_chars", 0) or 0),
            summary_chars=int(payload.get("summary_chars", 0) or 0),
            was_truncated=bool(payload.get("was_truncated", False)),
            summary_method=str(payload.get("summary_method", "deterministic_extractive_v1")),
        )


@dataclass
class ContextBudget:
    """Budget stats for assembled context package."""

    max_chars: int
    used_chars: int
    full_turns: int
    summarized_turns: int
    dropped_turns: int
    semantic_hits: int
    knowledge_hits: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_chars": int(self.max_chars),
            "used_chars": int(self.used_chars),
            "full_turns": int(self.full_turns),
            "summarized_turns": int(self.summarized_turns),
            "dropped_turns": int(self.dropped_turns),
            "semantic_hits": int(self.semantic_hits),
            "knowledge_hits": int(self.knowledge_hits),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ContextBudget":
        return cls(
            max_chars=int(payload.get("max_chars", 0) or 0),
            used_chars=int(payload.get("used_chars", 0) or 0),
            full_turns=int(payload.get("full_turns", 0) or 0),
            summarized_turns=int(payload.get("summarized_turns", 0) or 0),
            dropped_turns=int(payload.get("dropped_turns", 0) or 0),
            semantic_hits=int(payload.get("semantic_hits", 0) or 0),
            knowledge_hits=int(payload.get("knowledge_hits", 0) or 0),
        )


@dataclass
class ContextAssemblyTrace:
    """Safe trace metadata for context assembly decisions."""

    version: str
    recent_full_count: int
    summarized_count: int
    dropped_count: int
    semantic_hits_count: int
    knowledge_hits_count: int
    duplicates_removed: int
    budget_used_chars: int
    budget_limit_chars: int
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "recent_full_count": int(self.recent_full_count),
            "summarized_count": int(self.summarized_count),
            "dropped_count": int(self.dropped_count),
            "semantic_hits_count": int(self.semantic_hits_count),
            "knowledge_hits_count": int(self.knowledge_hits_count),
            "duplicates_removed": int(self.duplicates_removed),
            "budget_used_chars": int(self.budget_used_chars),
            "budget_limit_chars": int(self.budget_limit_chars),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ContextAssemblyTrace":
        raw_reasons = payload.get("reasons", [])
        reasons = [str(x) for x in raw_reasons] if isinstance(raw_reasons, list) else []
        return cls(
            version=str(payload.get("version", "context_assembly_trace_v1")),
            recent_full_count=int(payload.get("recent_full_count", 0) or 0),
            summarized_count=int(payload.get("summarized_count", 0) or 0),
            dropped_count=int(payload.get("dropped_count", 0) or 0),
            semantic_hits_count=int(payload.get("semantic_hits_count", 0) or 0),
            knowledge_hits_count=int(payload.get("knowledge_hits_count", 0) or 0),
            duplicates_removed=int(payload.get("duplicates_removed", 0) or 0),
            budget_used_chars=int(payload.get("budget_used_chars", 0) or 0),
            budget_limit_chars=int(payload.get("budget_limit_chars", 0) or 0),
            reasons=reasons,
        )


@dataclass
class ContextAssemblyPackage:
    """Assembled context package prepared for writer usage."""

    current_user_message: str
    recent_turns_full: list[TurnContextItem] = field(default_factory=list)
    recent_turns_summarized: list[TurnMicroSummary] = field(default_factory=list)
    pattern_core: str | None = None
    active_frame: dict[str, Any] | None = None
    personal_history_context: list[dict[str, Any]] = field(default_factory=list)
    semantic_memory_hits: list[dict[str, Any]] = field(default_factory=list)
    knowledge_rag_hits: list[dict[str, Any]] = field(default_factory=list)
    context_budget: ContextBudget = field(
        default_factory=lambda: ContextBudget(
            max_chars=0,
            used_chars=0,
            full_turns=0,
            summarized_turns=0,
            dropped_turns=0,
            semantic_hits=0,
            knowledge_hits=0,
        )
    )
    trace: ContextAssemblyTrace = field(
        default_factory=lambda: ContextAssemblyTrace(
            version="context_assembly_trace_v1",
            recent_full_count=0,
            summarized_count=0,
            dropped_count=0,
            semantic_hits_count=0,
            knowledge_hits_count=0,
            duplicates_removed=0,
            budget_used_chars=0,
            budget_limit_chars=0,
            reasons=[],
        )
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_user_message": self.current_user_message,
            "recent_turns_full": [item.to_dict() for item in self.recent_turns_full],
            "recent_turns_summarized": [item.to_dict() for item in self.recent_turns_summarized],
            "pattern_core": self.pattern_core,
            "active_frame": self.active_frame if isinstance(self.active_frame, dict) else {},
            "personal_history_context": list(self.personal_history_context),
            "semantic_memory_hits": list(self.semantic_memory_hits),
            "knowledge_rag_hits": list(self.knowledge_rag_hits),
            "context_budget": self.context_budget.to_dict(),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ContextAssemblyPackage":
        raw_full = payload.get("recent_turns_full", [])
        raw_summarized = payload.get("recent_turns_summarized", [])
        context_budget = payload.get("context_budget", {})
        trace = payload.get("trace", {})

        recent_full = [
            TurnContextItem.from_dict(item)
            for item in raw_full
            if isinstance(item, dict)
        ]
        recent_summarized = [
            TurnMicroSummary.from_dict(item)
            for item in raw_summarized
            if isinstance(item, dict)
        ]
        active_frame = payload.get("active_frame")
        return cls(
            current_user_message=str(payload.get("current_user_message", "")),
            recent_turns_full=recent_full,
            recent_turns_summarized=recent_summarized,
            pattern_core=str(payload.get("pattern_core", "")) or None,
            active_frame=active_frame if isinstance(active_frame, dict) else {},
            personal_history_context=list(payload.get("personal_history_context", [])),
            semantic_memory_hits=list(payload.get("semantic_memory_hits", [])),
            knowledge_rag_hits=list(payload.get("knowledge_rag_hits", [])),
            context_budget=(
                ContextBudget.from_dict(context_budget)
                if isinstance(context_budget, dict)
                else ContextBudget(
                    max_chars=0,
                    used_chars=0,
                    full_turns=0,
                    summarized_turns=0,
                    dropped_turns=0,
                    semantic_hits=0,
                    knowledge_hits=0,
                )
            ),
            trace=(
                ContextAssemblyTrace.from_dict(trace)
                if isinstance(trace, dict)
                else ContextAssemblyTrace(
                    version="context_assembly_trace_v1",
                    recent_full_count=0,
                    summarized_count=0,
                    dropped_count=0,
                    semantic_hits_count=0,
                    knowledge_hits_count=0,
                    duplicates_removed=0,
                    budget_used_chars=0,
                    budget_limit_chars=0,
                    reasons=[],
                )
            ),
        )
