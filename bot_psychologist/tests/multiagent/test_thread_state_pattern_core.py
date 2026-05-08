from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.thread_state import ArchivedThread, ThreadState


def test_thread_state_defaults_work_without_semantic_fields() -> None:
    state = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
    )
    assert state.pattern_core == ""
    assert state.active_frame == {}


def test_thread_state_to_dict_contains_semantic_fields() -> None:
    state = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        pattern_core="core",
        active_frame={"current_need": "support"},
    )
    payload = state.to_dict()
    assert payload["pattern_core"] == "core"
    assert payload["active_frame"]["current_need"] == "support"


def test_thread_state_from_dict_is_backward_compatible() -> None:
    payload = {
        "thread_id": "t1",
        "user_id": "u1",
        "core_direction": "topic",
        "phase": "clarify",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    restored = ThreadState.from_dict(payload)
    assert restored.pattern_core == ""
    assert restored.active_frame == {}


def test_thread_state_from_dict_normalizes_invalid_active_frame() -> None:
    payload = {
        "thread_id": "t1",
        "user_id": "u1",
        "core_direction": "topic",
        "phase": "clarify",
        "pattern_core": "core",
        "active_frame": ["bad", "type"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    restored = ThreadState.from_dict(payload)
    assert restored.pattern_core == "core"
    assert restored.active_frame == {}


def test_archived_thread_from_dict_backward_compatible() -> None:
    payload = {
        "thread_id": "old",
        "core_direction": "topic",
        "closed_loops": [],
        "open_loops": [],
        "final_phase": "clarify",
        "archived_at": datetime.utcnow().isoformat(),
        "archive_reason": "new_thread",
    }
    archived = ArchivedThread.from_dict(payload)
    assert archived.pattern_core == ""
    assert archived.active_frame == {}


def test_archived_thread_invalid_active_frame_is_normalized() -> None:
    payload = {
        "thread_id": "old",
        "core_direction": "topic",
        "closed_loops": [],
        "open_loops": [],
        "final_phase": "clarify",
        "archived_at": datetime.utcnow().isoformat(),
        "archive_reason": "new_thread",
        "pattern_core": "restored core",
        "active_frame": "bad",
    }
    archived = ArchivedThread.from_dict(payload)
    assert archived.pattern_core == "restored core"
    assert archived.active_frame == {}
