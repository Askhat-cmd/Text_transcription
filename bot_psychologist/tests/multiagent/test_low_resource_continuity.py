from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.thread_manager import ThreadManagerAgent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot


def _snapshot(*, intent: str, nervous_state: str = "window") -> StateSnapshot:
    return StateSnapshot(
        nervous_state=nervous_state,
        intent=intent,
        openness="mixed",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_qb010_like_low_resource_followup_keeps_thread() -> None:
    manager = ThreadManagerAgent()
    user_id = "qb010_like"

    turn1 = await manager.update(
        user_message="\u0421\u0438\u043b \u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=None,
        archived_threads=[],
    )
    turn2 = await manager.update(
        user_message="\u0414\u0430\u0436\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0442\u044c \u0442\u044f\u0436\u0435\u043b\u043e.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=turn1,
        archived_threads=[],
    )
    turn3 = await manager.update(
        user_message="\u041c\u043e\u0436\u043d\u043e \u0447\u0442\u043e-\u0442\u043e \u0441\u043e\u0432\u0441\u0435\u043c \u043f\u0440\u043e\u0441\u0442\u043e\u0435 \u043d\u0430 \u0441\u0435\u0439\u0447\u0430\u0441?",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=turn2,
        archived_threads=[],
    )

    debug = manager.last_debug
    assert turn3.relation_to_thread != "new_thread"
    assert turn3.phase == "clarify"
    assert turn3.response_mode in {"validate", "regulate", "practice"}
    assert debug["relation"]["relation_reason"] == "low_resource_continuation_marker"
    assert debug["phase"]["phase_reason"] == "low_resource_hold_phase"
    assert "low_resource_phase_hold" in debug["summary_flags"]
    assert debug["action"]["thread_action"] == "continue_thread"


@pytest.mark.asyncio
async def test_qb002_like_contact_hypo_is_validate() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="\u042f \u043e\u0447\u0435\u043d\u044c \u0443\u0441\u0442\u0430\u043b, \u043f\u0440\u043e\u0441\u0442\u043e \u043f\u043e\u0431\u0443\u0434\u044c \u0440\u044f\u0434\u043e\u043c.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id="qb002_like",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "validate"


@pytest.mark.asyncio
async def test_qb005_like_solution_window_is_practice() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="\u041a\u0430\u043a\u043e\u0439 \u043e\u0434\u0438\u043d \u0448\u0430\u0433 \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0441\u0435\u0433\u043e\u0434\u043d\u044f?",
        state_snapshot=_snapshot(intent="solution", nervous_state="window"),
        user_id="qb005_like",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "practice"


@pytest.mark.asyncio
async def test_low_resource_continuation_does_not_promote_to_explore() -> None:
    manager = ThreadManagerAgent()
    user_id = "phase_guard_low_resource"

    turn1 = await manager.update(
        user_message="No energy left.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=None,
        archived_threads=[],
    )
    turn2 = await manager.update(
        user_message="Even replying is hard.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=turn1,
        archived_threads=[],
    )
    turn3 = await manager.update(
        user_message="Something very simple right now, please.",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id=user_id,
        current_thread=turn2,
        archived_threads=[],
    )

    debug = manager.last_debug
    assert turn3.relation_to_thread == "continue"
    assert turn3.phase == "clarify"
    assert debug["phase"]["phase_reason"] == "low_resource_hold_phase"
    assert "low_resource_phase_hold" in debug["summary_flags"]


@pytest.mark.asyncio
async def test_window_clarify_continue_can_promote_to_explore() -> None:
    manager = ThreadManagerAgent()
    user_id = "phase_guard_window"

    turn1 = await manager.update(
        user_message="I want to understand why this keeps happening.",
        state_snapshot=_snapshot(intent="clarify", nervous_state="window"),
        user_id=user_id,
        current_thread=None,
        archived_threads=[],
    )
    turn2 = await manager.update(
        user_message="You are right, can you help me unpack this pattern?",
        state_snapshot=_snapshot(intent="clarify", nervous_state="window"),
        user_id=user_id,
        current_thread=turn1,
        archived_threads=[],
    )
    turn3 = await manager.update(
        user_message="You are right, I think it repeats when I am criticized.",
        state_snapshot=_snapshot(intent="clarify", nervous_state="window"),
        user_id=user_id,
        current_thread=turn2,
        archived_threads=[],
    )

    debug = manager.last_debug
    assert turn3.relation_to_thread == "continue"
    assert turn3.phase == "explore"
    assert debug["phase"]["phase_reason"] == "clarify_to_explore"
