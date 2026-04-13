from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes import _build_turn_diff


def test_turn_diff_for_first_turn_has_zero_deltas() -> None:
    diff = _build_turn_diff(
        None,
        {
            "recommended_mode": "PRESENCE",
            "user_state": "curious",
            "memory_turns": 1,
            "semantic_hits": 0,
            "config_snapshot": {"max_context_size": 2000},
        },
    )

    assert diff["route_changed"] is False
    assert diff["state_changed"] is False
    assert diff["config_changed_keys"] == []
    assert diff["memory_delta"]["turns_added"] == 0
    assert diff["memory_delta"]["summary_changed"] is False
    assert diff["memory_delta"]["semantic_hits_delta"] == 0


def test_turn_diff_detects_route_state_config_and_memory_changes() -> None:
    previous = {
        "recommended_mode": "PRESENCE",
        "user_state": "curious",
        "memory_turns": 3,
        "semantic_hits": 1,
        "summary_text": "old summary",
        "summary_last_turn": 3,
        "config_snapshot": {
            "max_context_size": 2000,
            "rerank_enabled": True,
        },
    }
    current = {
        "recommended_mode": "VALIDATION",
        "user_state": "overwhelmed",
        "memory_turns": 5,
        "semantic_hits": 4,
        "summary_text": "new summary",
        "summary_last_turn": 5,
        "config_snapshot": {
            "max_context_size": 2600,
            "rerank_enabled": True,
        },
    }

    diff = _build_turn_diff(previous, current)

    assert diff["route_changed"] is True
    assert diff["state_changed"] is True
    assert diff["config_changed_keys"] == ["max_context_size"]
    assert diff["memory_delta"]["turns_added"] == 2
    assert diff["memory_delta"]["summary_changed"] is True
    assert diff["memory_delta"]["semantic_hits_delta"] == 3
