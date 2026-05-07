from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.thread_manager import THREAD_DIAGNOSTICS_VERSION, ThreadManagerAgent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState


def _snapshot(*, intent: str = "explore", nervous_state: str = "window", safety: bool = False) -> StateSnapshot:
    return StateSnapshot(
        nervous_state=nervous_state,
        intent=intent,
        openness="open",
        ok_position="I+W+",
        safety_flag=safety,
        confidence=0.8,
    )


def _thread(*, core_direction: str = "anxiety before meeting") -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="t-active",
        user_id="u1",
        core_direction=core_direction,
        phase="clarify",
        turns_in_phase=2,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_diagnostics_new_thread_reason_no_current_thread() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="hello",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    debug = manager.last_debug
    assert debug["version"] == THREAD_DIAGNOSTICS_VERSION
    assert debug["action"]["thread_action"] == "new_thread"
    assert debug["relation"]["relation_reason"] == "no_current_thread"
    assert debug["phase"]["phase_reason"] == "new_thread_default_clarify"


@pytest.mark.asyncio
async def test_diagnostics_solution_mode_reason() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="what one step should I do today?",
        state_snapshot=_snapshot(intent="solution"),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    mode = manager.last_debug["mode"]
    assert mode["selected_mode"] == "practice"
    assert mode["mode_reason"] == "solution_practice"


@pytest.mark.asyncio
async def test_diagnostics_contact_mode_reason() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="just stay with me for a minute",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    mode = manager.last_debug["mode"]
    assert mode["selected_mode"] == "validate"
    assert mode["mode_reason"] == "explicit_contact_validate"


@pytest.mark.asyncio
async def test_diagnostics_low_continuity_new_thread_flag() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="how to cook pasta tonight with tomato sauce",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=_thread(core_direction="project criticism fear at work"),
        archived_threads=[],
    )
    debug = manager.last_debug
    assert debug["relation"]["relation_reason"] == "continuity_below_threshold"
    assert "low_continuity_new_thread" in debug["summary_flags"]


@pytest.mark.asyncio
async def test_diagnostics_followup_marker_reason() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="you are right, but how do I stop replaying this?",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=_thread(core_direction="social anxiety and self-criticism"),
        archived_threads=[],
    )
    debug = manager.last_debug
    assert debug["relation"]["relation_reason"] == "followup_continue_marker"
    assert debug["relation"]["selected_relation"] == "continue"


@pytest.mark.asyncio
async def test_diagnostics_branch_marker_hit() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="by the way anxiety before meeting also affects my sleep",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=_thread(core_direction="anxiety before meeting tomorrow"),
        archived_threads=[],
    )
    relation = manager.last_debug["relation"]
    assert relation["branch_marker_hit"] is True
    assert relation["selected_relation"] in {"branch", "new_thread"}


@pytest.mark.asyncio
async def test_low_resource_continuation_marker_diagnostics() -> None:
    manager = ThreadManagerAgent()
    current = _thread(core_direction="i feel depleted and very tired")
    updated = await manager.update(
        user_message="something very simple right now, no pressure please",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id="u1",
        current_thread=current,
        archived_threads=[],
    )
    debug = manager.last_debug
    assert updated.relation_to_thread == "continue"
    assert updated.phase == "clarify"
    assert debug["relation"]["low_resource_continue_marker_hit"] is True
    assert debug["relation"]["relation_reason"] == "low_resource_continuation_marker"
    assert debug["phase"]["phase_reason"] == "low_resource_hold_phase"
    assert "low_resource_followup_continued" in debug["summary_flags"]
    assert "low_resource_phase_hold" in debug["summary_flags"]
