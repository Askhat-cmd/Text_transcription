"""Writer contract used by multi-agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass

from .memory_bundle import MemoryBundle
from .thread_state import ThreadState


@dataclass
class WriterContract:
    """Stable payload that Writer receives for one response generation."""

    user_message: str
    thread_state: ThreadState
    memory_bundle: MemoryBundle
    response_language: str | None = None

    def to_dict(self) -> dict:
        return {
            "user_message": self.user_message,
            "thread_state": self.thread_state.to_dict(),
            "memory_bundle": self.memory_bundle.to_dict(),
            "response_language": self.response_language,
        }

    def to_prompt_context(self) -> dict:
        """Serialize context for Writer prompt templates."""
        return {
            "user_message": self.user_message,
            "phase": self.thread_state.phase,
            "response_mode": self.thread_state.response_mode,
            "response_goal": self.thread_state.response_goal,
            "must_avoid": self.thread_state.must_avoid,
            "ok_position": self.thread_state.ok_position,
            "openness": self.thread_state.openness,
            "open_loops": self.thread_state.open_loops,
            "closed_loops": self.thread_state.closed_loops,
            "core_direction": self.thread_state.core_direction,
            "nervous_state": self.thread_state.nervous_state,
            "safety_active": self.thread_state.safety_active,
            "conversation_context": self.memory_bundle.conversation_context,
            "user_profile_patterns": self.memory_bundle.user_profile.patterns,
            "user_profile_values": self.memory_bundle.user_profile.values,
            "semantic_hits": [hit.content for hit in self.memory_bundle.semantic_hits[:2]],
            "has_relevant_knowledge": self.memory_bundle.has_relevant_knowledge,
        }
