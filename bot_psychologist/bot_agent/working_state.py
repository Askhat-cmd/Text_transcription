"""Structured user working state for adaptive dialogue behavior."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WorkingState:
    """Current interpreted state of the user in the dialogue process."""

    dominant_state: str
    emotion: str
    defense: Optional[str] = None
    phase: str = "начало контакта"
    direction: str = "диагностика"
    last_updated_turn: int = 0
    confidence_level: str = "low"

    def to_dict(self) -> Dict:
        return {
            "dominant_state": self.dominant_state,
            "emotion": self.emotion,
            "defense": self.defense,
            "phase": self.phase,
            "direction": self.direction,
            "last_updated_turn": self.last_updated_turn,
            "confidence_level": self.confidence_level,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkingState":
        return cls(
            dominant_state=data.get("dominant_state", "неопределено"),
            emotion=data.get("emotion", "неопределено"),
            defense=data.get("defense"),
            phase=data.get("phase", "начало контакта"),
            direction=data.get("direction", "диагностика"),
            last_updated_turn=int(data.get("last_updated_turn", 0)),
            confidence_level=data.get("confidence_level", "low"),
        )

    def get_user_stage(self) -> str:
        """Map phase to stage-filter level."""
        stage_map = {
            "начало контакта": "surface",
            "осмысление": "awareness",
            "работа": "exploration",
            "интеграция": "integration",
        }
        return stage_map.get(self.phase, "surface")
