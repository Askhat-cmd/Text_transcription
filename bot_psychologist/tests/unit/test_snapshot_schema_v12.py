from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v12 import build_snapshot_v12, validate_snapshot_v12


def test_snapshot_schema_v12_validates_required_fields() -> None:
    snapshot = build_snapshot_v12(
        diagnostics={
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "avoidance pattern",
            "optional": {"active_quadrant": "i"},
        },
        route="reflect",
        summary_staleness="fresh",
    )
    valid, errors = validate_snapshot_v12(snapshot)
    assert valid is True
    assert errors == []


def test_snapshot_schema_v12_rejects_invalid_enums() -> None:
    snapshot = {
        "_schema_version": "1.2",
        "nervous_system_state": "bad",
        "request_function": "bad",
        "dominant_part": "x",
        "active_quadrant": "bad",
        "core_theme": "",
        "last_practice_channel": None,
        "active_track": None,
        "insights_log": "bad",
    }
    valid, errors = validate_snapshot_v12(snapshot)
    assert valid is False
    assert len(errors) >= 3
