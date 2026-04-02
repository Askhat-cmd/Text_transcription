from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.practice_schema import parse_practice_entry, validate_practice_entry


def test_practice_schema_v1_valid_entry() -> None:
    payload = {
        "id": "p1",
        "title": "Шаг",
        "channel": "body",
        "scientific_basis": "polyvagal",
        "triggers": ["practice"],
        "nervous_system_states": ["hyper"],
        "request_functions": ["discharge"],
        "core_themes": ["тревога"],
        "instruction": "Дыши",
        "micro_tuning": "медленно",
        "closure": "заметь эффект",
        "time_limit_minutes": 2,
        "contraindications": [],
    }
    valid, errors = validate_practice_entry(payload)
    assert valid is True
    assert errors == []
    entry = parse_practice_entry(payload)
    assert entry.id == "p1"
    assert entry.time_limit_minutes == 2


def test_practice_schema_v1_rejects_malformed_entry() -> None:
    payload = {"id": "broken"}
    valid, errors = validate_practice_entry(payload)
    assert valid is False
    assert "missing_title" in errors
    assert "missing_time_limit_minutes" in errors

