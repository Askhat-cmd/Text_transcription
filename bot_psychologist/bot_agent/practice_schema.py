"""Practice engine schema v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class PracticeEntry:
    id: str
    title: str
    channel: str
    scientific_basis: str
    triggers: List[str]
    nervous_system_states: List[str]
    request_functions: List[str]
    core_themes: List[str]
    instruction: str
    micro_tuning: str
    closure: str
    time_limit_minutes: int
    contraindications: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "channel": self.channel,
            "scientific_basis": self.scientific_basis,
            "triggers": list(self.triggers),
            "nervous_system_states": list(self.nervous_system_states),
            "request_functions": list(self.request_functions),
            "core_themes": list(self.core_themes),
            "instruction": self.instruction,
            "micro_tuning": self.micro_tuning,
            "closure": self.closure,
            "time_limit_minutes": int(self.time_limit_minutes),
            "contraindications": list(self.contraindications),
        }


REQUIRED_FIELDS = (
    "id",
    "title",
    "channel",
    "scientific_basis",
    "triggers",
    "nervous_system_states",
    "request_functions",
    "core_themes",
    "instruction",
    "micro_tuning",
    "closure",
    "time_limit_minutes",
    "contraindications",
)


def validate_practice_entry(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return False, ["entry_not_dict"]
    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"missing_{field}")

    for list_field in (
        "triggers",
        "nervous_system_states",
        "request_functions",
        "core_themes",
        "contraindications",
    ):
        if list_field in payload and not isinstance(payload.get(list_field), list):
            errors.append(f"invalid_{list_field}")

    if "time_limit_minutes" in payload:
        try:
            minutes = int(payload.get("time_limit_minutes"))
            if minutes <= 0:
                errors.append("invalid_time_limit_minutes")
        except Exception:
            errors.append("invalid_time_limit_minutes")

    return len(errors) == 0, errors


def parse_practice_entry(payload: Dict[str, Any]) -> PracticeEntry:
    valid, errors = validate_practice_entry(payload)
    if not valid:
        raise ValueError(f"invalid practice entry: {', '.join(errors)}")
    return PracticeEntry(
        id=str(payload["id"]),
        title=str(payload["title"]),
        channel=str(payload["channel"]),
        scientific_basis=str(payload["scientific_basis"]),
        triggers=[str(x) for x in payload.get("triggers", [])],
        nervous_system_states=[str(x) for x in payload.get("nervous_system_states", [])],
        request_functions=[str(x) for x in payload.get("request_functions", [])],
        core_themes=[str(x) for x in payload.get("core_themes", [])],
        instruction=str(payload["instruction"]),
        micro_tuning=str(payload["micro_tuning"]),
        closure=str(payload["closure"]),
        time_limit_minutes=int(payload["time_limit_minutes"]),
        contraindications=[str(x) for x in payload.get("contraindications", [])],
    )

