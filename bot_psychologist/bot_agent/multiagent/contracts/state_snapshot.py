"""State snapshot contract from State Analyzer to Thread Manager."""

from __future__ import annotations

from dataclasses import dataclass


_NERVOUS_STATES = {"window", "hyper", "hypo"}
_INTENTS = {"clarify", "vent", "explore", "contact", "solution"}
_OPENNESS = {"open", "mixed", "defensive", "collapsed"}
_OK_POSITIONS = {"I+W+", "I-W+", "I+W-", "I-W-"}


@dataclass(frozen=True)
class StateSnapshot:
    """Compact state signal for one turn."""

    nervous_state: str
    intent: str
    openness: str
    ok_position: str
    safety_flag: bool
    confidence: float

    def __post_init__(self) -> None:
        if self.nervous_state not in _NERVOUS_STATES:
            raise ValueError(f"Invalid nervous_state: {self.nervous_state}")
        if self.intent not in _INTENTS:
            raise ValueError(f"Invalid intent: {self.intent}")
        if self.openness not in _OPENNESS:
            raise ValueError(f"Invalid openness: {self.openness}")
        if self.ok_position not in _OK_POSITIONS:
            raise ValueError(f"Invalid ok_position: {self.ok_position}")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(f"Invalid confidence: {self.confidence}")

    def to_dict(self) -> dict:
        return {
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
            "safety_flag": self.safety_flag,
            "confidence": self.confidence,
        }

