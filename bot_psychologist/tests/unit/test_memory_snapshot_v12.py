from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_updater import memory_updater


def _memory_stub() -> SimpleNamespace:
    return SimpleNamespace(
        summary="Короткое резюме.",
        summary_updated_at=3,
        turns=[],
        metadata={
            "last_practice_channel": "body",
            "active_track": "stability",
            "insights_log": ["insight-1"],
        },
        save_to_disk=lambda: None,
    )


def test_snapshot_v12_contains_required_fields() -> None:
    memory = _memory_stub()
    diagnostics = {
        "nervous_system_state": "hyper",
        "request_function": "solution",
        "core_theme": "panic before meeting",
        "optional": {
            "dominant_part": "anxious manager",
            "active_quadrant": "we",
        },
    }
    result = memory_updater.build_runtime_context(
        memory=memory,
        diagnostics=diagnostics,
        route="contact_hold",
    )

    snapshot = result.snapshot
    required = {
        "nervous_system_state",
        "request_function",
        "dominant_part",
        "active_quadrant",
        "core_theme",
        "last_practice_channel",
        "active_track",
        "insights_log",
    }
    assert required.issubset(snapshot.keys())
    assert snapshot["nervous_system_state"] == "hyper"
    assert snapshot["request_function"] == "solution"
    assert snapshot["dominant_part"] == "anxious manager"
    assert snapshot["active_quadrant"] == "we"
    assert "user_state" not in snapshot


def test_save_snapshot_v12_writes_active_keys() -> None:
    memory = _memory_stub()
    result = memory_updater.build_runtime_context(
        memory=memory,
        diagnostics={"nervous_system_state": "window"},
        route="reflect",
    )

    memory_updater.save_snapshot(memory, result.snapshot)
    assert memory.metadata["laststatesnapshot"] == result.snapshot
    assert memory.metadata["last_state_snapshot_v12"] == result.snapshot
    assert "last_state_snapshot_v11" not in memory.metadata
