from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState


def test_state_snapshot_valid() -> None:
    snapshot = StateSnapshot(
        nervous_state="window",
        intent="explore",
        openness="open",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.8,
    )
    assert snapshot.to_dict()["intent"] == "explore"


def test_state_snapshot_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        StateSnapshot(
            nervous_state="bad",
            intent="explore",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.8,
        )


def test_thread_state_roundtrip() -> None:
    state = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        continuity_score=0.6,
        turns_in_phase=2,
    )
    restored = ThreadState.from_dict(state.to_dict())
    assert restored.thread_id == "t1"
    assert restored.phase == "clarify"
    assert restored.continuity_score == 0.6


def test_thread_state_safety_forces_safe_override() -> None:
    state = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
        safety_active=True,
    )
    assert state.response_mode == "safe_override"


def test_thread_state_updated_not_earlier_than_created() -> None:
    created = datetime.utcnow()
    updated = created - timedelta(seconds=5)
    state = ThreadState(
        thread_id="t2",
        user_id="u2",
        core_direction="topic",
        phase="clarify",
        created_at=created,
        updated_at=updated,
    )
    assert state.updated_at == created

