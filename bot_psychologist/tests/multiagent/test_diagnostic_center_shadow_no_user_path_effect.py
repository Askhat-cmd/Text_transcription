from __future__ import annotations

import sys
import importlib
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="shadow_effect_t",
        user_id="u1",
        core_direction="x",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        continuity_score=0.9,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_shadow_does_not_change_writer_path(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    captured_contract = {}

    async def _write(contract):
        captured_contract["prompt_context"] = contract.to_prompt_context()
        return "writer answer"

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(return_value=StateSnapshot("window", "explore", "open", "I+W+", False, 0.8)),
    )
    monkeypatch.setattr(
        orch_module.thread_manager_agent,
        "update",
        AsyncMock(return_value=_thread()),
    )
    orch_module.thread_manager_agent.last_debug = {
        "version": "thread_diagnostics_v1",
        "relation": {"continuity_risk": "none"},
        "phase": {},
        "mode": {},
        "loops": {},
        "action": {"thread_action": "continue"},
        "summary_flags": [],
    }
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", has_relevant_knowledge=False, context_turns=2)),
    )
    monkeypatch.setattr(orch_module.writer_agent, "write", _write)
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _a, _c: ValidationResult(is_blocked=False),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.thread_storage, "archive_thread", lambda *_a, **_k: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])

    result = await MultiAgentOrchestrator().run(query="hello", user_id="u1")
    shadow = result["debug"]["diagnostic_center_shadow"]
    assert result["answer"] == "writer answer"
    assert shadow["runtime_mode"] == "shadow_only"
    assert shadow["user_path_effect"] == "none"
    assert shadow["divergence"]["user_path"]["writer_contract_changed"] is False
    assert shadow["divergence"]["user_path"]["writer_prompt_changed_by_shadow"] is False
    assert shadow["divergence"]["user_path"]["final_answer_changed_by_shadow"] is False
    prompt_context = captured_contract["prompt_context"]
    assert "diagnostic_center_shadow" not in str(prompt_context).lower()
    assert "diagnostic_center_output" not in str(prompt_context).lower()
