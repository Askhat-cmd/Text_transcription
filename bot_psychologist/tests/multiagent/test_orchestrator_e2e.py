from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ArchivedThread, ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _snapshot(*, safety_flag: bool = False) -> StateSnapshot:
    return StateSnapshot(
        nervous_state="window",
        intent="explore",
        openness="open",
        ok_position="I+W+",
        safety_flag=safety_flag,
        confidence=0.81,
    )


def _thread(
    *,
    thread_id: str = "t1",
    relation: str = "continue",
    phase: str = "clarify",
    response_mode: str = "reflect",
) -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id=thread_id,
        user_id="u1",
        core_direction="понять, что со мной происходит",
        phase=phase,  # type: ignore[arg-type]
        relation_to_thread=relation,  # type: ignore[arg-type]
        response_mode=response_mode,  # type: ignore[arg-type]
        continuity_score=0.87,
        created_at=now,
        updated_at=now,
    )


def _bundle(*, has_knowledge: bool = True, context_turns: int = 6) -> MemoryBundle:
    return MemoryBundle(
        conversation_context="User: привет\nAssistant: привет",
        has_relevant_knowledge=has_knowledge,
        context_turns=context_turns,
    )


def _archived() -> list[ArchivedThread]:
    return [
        ArchivedThread(
            thread_id="old_1",
            core_direction="старый контекст",
            closed_loops=[],
            open_loops=["незавершенный вопрос"],
            final_phase="explore",
            archived_at=datetime.utcnow(),
            archive_reason="new_thread",
        )
    ]


def _patch_pipeline(
    monkeypatch,
    *,
    analyzer_safety: bool = False,
    active_thread: ThreadState | None = None,
    archived_threads: list[ArchivedThread] | None = None,
    updated_thread: ThreadState | None = None,
    draft_answer: str = "Нормальный рабочий ответ без риска.",
    validation_result: ValidationResult | None = None,
) -> tuple[MultiAgentOrchestrator, dict]:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    tracker: dict[str, object] = {"saved_thread": None, "archived": [], "create_task_called": False}

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(return_value=_snapshot(safety_flag=analyzer_safety)),
    )
    monkeypatch.setattr(
        orch_module.thread_manager_agent,
        "update",
        AsyncMock(return_value=updated_thread or _thread()),
    )
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=_bundle()),
    )
    monkeypatch.setattr(
        orch_module.writer_agent,
        "write",
        AsyncMock(return_value=draft_answer),
    )
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _answer, _contract: validation_result or ValidationResult(is_blocked=False),
    )

    async_update = AsyncMock(return_value=None)
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", async_update)
    tracker["memory_update_mock"] = async_update

    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: active_thread)
    monkeypatch.setattr(
        orch_module.thread_storage,
        "load_archived",
        lambda _u: list(archived_threads or []),
    )

    def _save_active(thread: ThreadState) -> None:
        tracker["saved_thread"] = thread

    def _archive_thread(thread: ThreadState, reason: str = "new_thread") -> None:
        tracker["archived"].append((thread, reason))

    monkeypatch.setattr(orch_module.thread_storage, "save_active", _save_active)
    monkeypatch.setattr(orch_module.thread_storage, "archive_thread", _archive_thread)

    def _capture_task(coro):
        tracker["create_task_called"] = True
        coro.close()
        return None

    monkeypatch.setattr(orch_module.asyncio, "create_task", _capture_task)

    return MultiAgentOrchestrator(), tracker


@pytest.mark.asyncio
async def test_e2e_01_full_pipeline_returns_dict(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="привет", user_id="u1")
    assert isinstance(result, dict)
    for key in ("status", "answer", "thread_id", "phase"):
        assert key in result


@pytest.mark.asyncio
async def test_e2e_02_answer_non_empty(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch, draft_answer="Содержательный ответ.")
    result = await orchestrator.run(query="привет", user_id="u1")
    assert isinstance(result["answer"], str)
    assert result["answer"].strip() != ""


@pytest.mark.asyncio
async def test_e2e_03_debug_all_fields(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="привет", user_id="u1")
    debug = result["debug"]
    for key in (
        "nervous_state",
        "intent",
        "safety_flag",
        "confidence",
        "has_relevant_knowledge",
        "context_turns",
        "semantic_hits_count",
        "validator_blocked",
        "validator_block_reason",
        "validator_quality_flags",
    ):
        assert key in debug


@pytest.mark.asyncio
async def test_e2e_04_status_ok(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_e2e_05_phase_valid(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch, updated_thread=_thread(phase="integrate"))
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["phase"] in {"clarify", "explore", "stabilize", "integrate"}


@pytest.mark.asyncio
async def test_e2e_06_response_mode_valid(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch, updated_thread=_thread(response_mode="practice"))
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["response_mode"] in {
        "reflect",
        "validate",
        "explore",
        "regulate",
        "practice",
        "safe_override",
    }


@pytest.mark.asyncio
async def test_e2e_07_safety_override_flow(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(
        monkeypatch,
        analyzer_safety=True,
        updated_thread=_thread(response_mode="safe_override"),
    )
    result = await orchestrator.run(query="сейчас плохо", user_id="u1")
    assert result["response_mode"] == "safe_override"
    assert result["answer"].strip() != ""


@pytest.mark.asyncio
async def test_e2e_08_validator_blocked_flow(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(
        monkeypatch,
        draft_answer="Опасный ответ",
        validation_result=ValidationResult(
            is_blocked=True,
            block_reason="safety",
            safe_replacement="Безопасная замена",
            quality_flags=["blocked"],
        ),
    )
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["answer"] == "Безопасная замена"
    assert result["debug"]["validator_blocked"] is True


@pytest.mark.asyncio
async def test_e2e_09_memory_update_called(monkeypatch) -> None:
    orchestrator, tracker = _patch_pipeline(monkeypatch)
    await orchestrator.run(query="привет", user_id="u1")
    assert tracker["create_task_called"] is True
    assert tracker["memory_update_mock"].call_count == 1


@pytest.mark.asyncio
async def test_e2e_10_thread_saved(monkeypatch) -> None:
    updated = _thread(thread_id="saved_1")
    orchestrator, tracker = _patch_pipeline(monkeypatch, updated_thread=updated)
    await orchestrator.run(query="привет", user_id="u1")
    assert tracker["saved_thread"] is not None
    assert tracker["saved_thread"].thread_id == "saved_1"


@pytest.mark.asyncio
async def test_e2e_11_new_thread_archived(monkeypatch) -> None:
    current = _thread(thread_id="old_active")
    updated = _thread(thread_id="new_active", relation="new_thread")
    orchestrator, tracker = _patch_pipeline(
        monkeypatch,
        active_thread=current,
        archived_threads=_archived(),
        updated_thread=updated,
    )
    await orchestrator.run(query="новая тема", user_id="u1")
    assert len(tracker["archived"]) == 1
    assert tracker["archived"][0][0].thread_id == "old_active"


@pytest.mark.asyncio
async def test_e2e_12_continue_thread(monkeypatch) -> None:
    current = _thread(thread_id="same_thread")
    updated = _thread(thread_id="same_thread", relation="continue")
    orchestrator, tracker = _patch_pipeline(
        monkeypatch,
        active_thread=current,
        updated_thread=updated,
    )
    result = await orchestrator.run(query="продолжаем", user_id="u1")
    assert result["thread_id"] == "same_thread"
    assert len(tracker["archived"]) == 0


def test_e2e_13_run_sync_equivalent(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    expected = asyncio.run(orchestrator.run(query="привет", user_id="u1"))
    actual = orchestrator.run_sync(query="привет", user_id="u1")
    assert actual == expected


@pytest.mark.asyncio
async def test_e2e_14_empty_query(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="", user_id="u1")
    assert isinstance(result, dict)
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_e2e_15_long_query(monkeypatch) -> None:
    orchestrator, _ = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="а" * 2500, user_id="u1")
    assert isinstance(result, dict)
    assert result["status"] == "ok"
