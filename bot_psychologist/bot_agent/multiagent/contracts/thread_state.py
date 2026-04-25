"""Thread state contracts for Thread Manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


PhaseType = Literal["stabilize", "clarify", "explore", "integrate"]
RelationType = Literal["continue", "branch", "new_thread", "return_to_old"]
ResponseModeType = Literal[
    "reflect",
    "validate",
    "explore",
    "regulate",
    "practice",
    "safe_override",
]

_PHASES = {"stabilize", "clarify", "explore", "integrate"}
_RELATIONS = {"continue", "branch", "new_thread", "return_to_old"}
_RESPONSE_MODES = {"reflect", "validate", "explore", "regulate", "practice", "safe_override"}


@dataclass
class ThreadState:
    """Live thread state used by writer and orchestrator."""

    thread_id: str
    user_id: str
    core_direction: str
    phase: PhaseType

    open_loops: list[str] = field(default_factory=list)
    closed_loops: list[str] = field(default_factory=list)

    nervous_state: str = "window"
    intent: str = "explore"
    openness: str = "open"
    ok_position: str = "I+W+"

    relation_to_thread: RelationType = "continue"
    response_goal: str = ""
    response_mode: ResponseModeType = "reflect"
    must_avoid: list[str] = field(default_factory=list)

    continuity_score: float = 1.0
    turns_in_phase: int = 1
    last_meaningful_shift: str = ""

    safety_active: bool = False

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.phase not in _PHASES:
            raise ValueError(f"Invalid phase: {self.phase}")
        if self.relation_to_thread not in _RELATIONS:
            raise ValueError(f"Invalid relation_to_thread: {self.relation_to_thread}")
        if self.response_mode not in _RESPONSE_MODES:
            raise ValueError(f"Invalid response_mode: {self.response_mode}")
        if not (0.0 <= float(self.continuity_score) <= 1.0):
            raise ValueError(f"Invalid continuity_score: {self.continuity_score}")
        if int(self.turns_in_phase) < 1:
            self.turns_in_phase = 1
        if self.safety_active and self.response_mode != "safe_override":
            self.response_mode = "safe_override"
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "core_direction": self.core_direction,
            "phase": self.phase,
            "open_loops": self.open_loops,
            "closed_loops": self.closed_loops,
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
            "relation_to_thread": self.relation_to_thread,
            "response_goal": self.response_goal,
            "response_mode": self.response_mode,
            "must_avoid": self.must_avoid,
            "continuity_score": self.continuity_score,
            "turns_in_phase": self.turns_in_phase,
            "last_meaningful_shift": self.last_meaningful_shift,
            "safety_active": self.safety_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThreadState":
        payload = dict(data)
        created_at_raw = payload.get("created_at")
        updated_at_raw = payload.get("updated_at")
        payload["created_at"] = (
            datetime.fromisoformat(created_at_raw)
            if isinstance(created_at_raw, str)
            else datetime.utcnow()
        )
        payload["updated_at"] = (
            datetime.fromisoformat(updated_at_raw)
            if isinstance(updated_at_raw, str)
            else payload["created_at"]
        )
        return cls(**payload)


@dataclass
class ArchivedThread:
    """Archived thread state snapshot."""

    thread_id: str
    core_direction: str
    closed_loops: list[str]
    open_loops: list[str]
    final_phase: str
    archived_at: datetime
    archive_reason: str

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "core_direction": self.core_direction,
            "closed_loops": self.closed_loops,
            "open_loops": self.open_loops,
            "final_phase": self.final_phase,
            "archived_at": self.archived_at.isoformat(),
            "archive_reason": self.archive_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArchivedThread":
        payload = dict(data)
        archived_at_raw = payload.get("archived_at")
        payload["archived_at"] = (
            datetime.fromisoformat(archived_at_raw)
            if isinstance(archived_at_raw, str)
            else datetime.utcnow()
        )
        return cls(**payload)

