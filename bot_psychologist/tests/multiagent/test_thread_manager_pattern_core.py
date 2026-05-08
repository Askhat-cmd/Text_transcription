from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.thread_manager import ThreadManagerAgent
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


def _thread(*, pattern_core: str = "existing core") -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="anxiety before meeting and fear of judgement",
        pattern_core=pattern_core,
        active_frame={"current_need": "warm contact and validation"},
        phase="clarify",
        turns_in_phase=2,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_new_thread_contact_hypo_gets_semantic_frame() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="just stay with me, no pressure",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    assert updated.pattern_core
    assert updated.active_frame.get("current_need") == "short support without pressure"
    assert updated.active_frame.get("next_recommended_direction") == "keep answer short and low pressure"


@pytest.mark.asyncio
async def test_new_thread_solution_gets_micro_step_direction() -> None:
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="what concrete step should I do today",
        state_snapshot=_snapshot(intent="solution"),
        user_id="u1",
        current_thread=None,
        archived_threads=[],
    )
    assert "next step" in updated.pattern_core.lower()
    assert updated.active_frame.get("current_need") == "one concrete next step"
    assert updated.active_frame.get("next_recommended_direction") == "offer one executable micro-step"


@pytest.mark.asyncio
async def test_continue_preserves_existing_pattern_core() -> None:
    manager = ThreadManagerAgent()
    current = _thread(pattern_core="stable continuity core")
    updated = await manager.update(
        user_message="you are right, about this anxiety before meeting what can I do",
        state_snapshot=_snapshot(intent="solution"),
        user_id="u1",
        current_thread=current,
        archived_threads=[],
    )
    assert updated.relation_to_thread == "continue"
    assert updated.pattern_core == "stable continuity core"


@pytest.mark.asyncio
async def test_safety_patch_preserves_pattern_core_and_sets_safety_need() -> None:
    manager = ThreadManagerAgent()
    current = _thread(pattern_core="do not lose this core")
    updated = await manager.update(
        user_message="panic and unsafe thoughts",
        state_snapshot=_snapshot(intent="contact", nervous_state="hyper", safety=True),
        user_id="u1",
        current_thread=current,
        archived_threads=[],
    )
    assert updated.pattern_core == "do not lose this core"
    assert updated.active_frame.get("current_need") == "immediate safety and stabilization"
    assert updated.active_frame.get("next_recommended_direction") == "prioritize safety"


@pytest.mark.asyncio
async def test_diagnostics_contains_semantic_frame_block() -> None:
    manager = ThreadManagerAgent()
    await manager.update(
        user_message="something very simple right now, no pressure",
        state_snapshot=_snapshot(intent="contact", nervous_state="hypo"),
        user_id="u1",
        current_thread=_thread(),
        archived_threads=[],
    )
    semantic = manager.last_debug.get("semantic_frame")
    assert isinstance(semantic, dict)
    assert semantic.get("pattern_core_present") is True
    assert semantic.get("active_frame_present") is True
    assert "current_need" in semantic.get("active_frame_keys", [])
