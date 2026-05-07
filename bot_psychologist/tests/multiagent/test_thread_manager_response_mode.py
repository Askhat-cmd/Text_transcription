from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.thread_manager import thread_manager_agent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot


@pytest.mark.asyncio
async def test_contact_with_hypo_routes_to_validate() -> None:
    snapshot = StateSnapshot(
        nervous_state="hypo",
        intent="contact",
        openness="mixed",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.9,
    )
    updated = await thread_manager_agent.update(
        user_message="Я устал, просто побудь рядом.",
        state_snapshot=snapshot,
        user_id="tm_case_contact",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "validate"


@pytest.mark.asyncio
async def test_hypo_without_contact_routes_to_regulate() -> None:
    snapshot = StateSnapshot(
        nervous_state="hypo",
        intent="clarify",
        openness="mixed",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.9,
    )
    updated = await thread_manager_agent.update(
        user_message="Нет сил, помоги понять почему так.",
        state_snapshot=snapshot,
        user_id="tm_case_hypo",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "regulate"


@pytest.mark.asyncio
async def test_solution_on_new_thread_routes_to_practice() -> None:
    snapshot = StateSnapshot(
        nervous_state="window",
        intent="solution",
        openness="open",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.9,
    )
    updated = await thread_manager_agent.update(
        user_message="Какой один шаг сделать сегодня?",
        state_snapshot=snapshot,
        user_id="tm_case_solution",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "practice"


@pytest.mark.asyncio
async def test_safety_routes_to_safe_override() -> None:
    snapshot = StateSnapshot(
        nervous_state="hyper",
        intent="contact",
        openness="collapsed",
        ok_position="I-W-",
        safety_flag=True,
        confidence=0.99,
    )
    updated = await thread_manager_agent.update(
        user_message="Мне очень плохо.",
        state_snapshot=snapshot,
        user_id="tm_case_safety",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.response_mode == "safe_override"
