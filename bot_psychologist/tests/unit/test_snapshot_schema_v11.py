from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v11 import build_snapshot_v11, validate_snapshot_v11


def test_snapshot_schema_v11_validates_required_fields() -> None:
    snapshot = build_snapshot_v11(
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "avoidance pattern",
        },
        route="reflect",
        summary_staleness="fresh",
    )
    valid, errors = validate_snapshot_v11(snapshot)
    assert valid is True
    assert errors == []


def test_snapshot_schema_v11_rejects_invalid_enums() -> None:
    snapshot = {
        "schema_version": "1.1",
        "diagnostics": {
            "interaction_mode": "bad",
            "nervous_system_state": "bad",
            "request_function": "bad",
            "core_theme": "",
        },
        "routing": {"last_route": "bad"},
        "meta": {"summary_staleness": "bad"},
    }
    valid, errors = validate_snapshot_v11(snapshot)
    assert valid is False
    assert len(errors) >= 4
