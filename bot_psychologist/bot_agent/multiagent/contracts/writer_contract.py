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

    def to_dict(self) -> dict:
        return {
            "user_message": self.user_message,
            "thread_state": self.thread_state.to_dict(),
            "memory_bundle": self.memory_bundle.to_dict(),
        }

