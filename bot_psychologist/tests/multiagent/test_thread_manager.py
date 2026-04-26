from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.thread_manager import ThreadManagerAgent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ArchivedThread, ThreadState


def _snapshot(
    *,
    safety: bool = False,
    nervous_state: str = "window",
    intent: str = "explore",
) -> StateSnapshot:
    return StateSnapshot(
        nervous_state=nervous_state,
        intent=intent,
        openness="open",
        ok_position="I+W+",
        safety_flag=safety,
        confidence=0.8,
    )


def _thread(user_id: str = "u1") -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id=user_id,
        core_direction="anxiety before meeting",
        phase="clarify",
        turns_in_phase=2,
    )


@pytest.mark.asyncio
async def test_first_message_creates_new_thread() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="hello there",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.relation_to_thread == "new_thread"
    assert updated.user_id == "u1"


@pytest.mark.asyncio
async def test_new_topic_creates_new_thread() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="how to optimize SQL indexes in production?",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=_thread(),
        archived_threads=[],
    )
    assert updated.relation_to_thread in {"new_thread", "branch"}


@pytest.mark.asyncio
async def test_safety_forces_safe_override() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="panic and unsafe thoughts",
        state_snapshot=_snapshot(safety=True, nervous_state="hyper"),
        user_id="u1",
        current_thread=_thread(),
        archived_threads=[],
    )
    assert updated.response_mode == "safe_override"
    assert updated.phase == "stabilize"


@pytest.mark.asyncio
async def test_return_to_old_restores_archived_thread() -> None:
    manager = ThreadManagerAgent()
    archived = [
        ArchivedThread(
            thread_id="old-thread",
            core_direction="same topic history",
            closed_loops=["loop1"],
            open_loops=["loop2"],
            final_phase="explore",
            archived_at=datetime.utcnow(),
            archive_reason="new_thread",
        )
    ]
    updated = await manager.update(
        user_message="can we return to same topic history",
        state_snapshot=_snapshot(),
        user_id="u1",
        current_thread=_thread(),
        archived_threads=archived,
    )
    assert updated.relation_to_thread == "return_to_old"
    assert updated.thread_id == "old-thread"


@pytest.mark.asyncio
async def test_russian_followup_question_keeps_continuity() -> None:
    manager = ThreadManagerAgent()
    current = ThreadState(
        thread_id="ru-thread-1",
        user_id="u-ru",
        core_direction="я чувствую сильную тревогу перед важным собеседованием завтра",
        phase="clarify",
        turns_in_phase=1,
    )
    updated = await manager.update(
        user_message="ты права, но как мне не думать об этом постоянно?",
        state_snapshot=_snapshot(intent="solution"),
        user_id="u-ru",
        current_thread=current,
        archived_threads=[],
    )
    assert updated.thread_id == "ru-thread-1"
    assert updated.relation_to_thread == "continue"


def test_update_is_coroutine() -> None:
    manager = ThreadManagerAgent()
    assert asyncio.iscoroutinefunction(manager.update)
