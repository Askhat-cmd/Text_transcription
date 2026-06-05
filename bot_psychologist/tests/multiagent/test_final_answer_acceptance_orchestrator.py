from __future__ import annotations

import importlib

import pytest

from .test_orchestrator_e2e import _patch_pipeline


@pytest.mark.asyncio
async def test_acceptance_gate_retries_stale_concrete_answer(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    stale = (
        "Сейчас полезнее прямое объяснение механизма: автоматический контроль может перегружать "
        "внимание еще до действия."
    )
    repaired = (
        "В твоей ситуации узел держится не в одном месте: семья давит, сокращение на работе усиливает "
        "ощущение невостребованности, а возраст 50 звучит как внутренний приговор. Распутывать это лучше "
        "через разделение фактов и убеждений: факт - работа изменилась, убеждение - будто ты бесполезен."
    )
    orchestrator, tracker = _patch_pipeline(monkeypatch, draft_answer=stale)
    orch_module.writer_agent.write.side_effect = [stale, repaired]

    result = await orchestrator.run(
        query="Мне 50, в семье напряжение, на работе сокращение, я в ступоре и чувствую невостребованность. Как распутать этот узел?",
        user_id="u1",
    )

    gate = result["debug"]["final_answer_acceptance_gate"]
    assert result["answer"] == repaired
    assert gate["status"] == "passed"
    assert gate["retry"]["attempted"] is True
    assert tracker["memory_update_mock"].call_count == 1


@pytest.mark.asyncio
async def test_acceptance_gate_quarantines_failed_answer(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    stale = (
        "Сейчас полезнее прямое объяснение механизма: автоматический контроль может перегружать "
        "внимание еще до действия."
    )
    orchestrator, tracker = _patch_pipeline(monkeypatch, draft_answer=stale)
    orch_module.writer_agent.write.side_effect = [stale, stale]

    result = await orchestrator.run(
        query="Мне 50, в семье напряжение, на работе сокращение, я в ступоре и чувствую невостребованность. Как распутать этот узел?",
        user_id="u1",
    )

    gate = result["debug"]["final_answer_acceptance_gate"]
    unanswered = result["debug"]["unanswered_question_state"]
    assert gate["status"] == "failed"
    assert gate["must_quarantine_answer"] is True
    assert tracker["memory_update_mock"].call_count == 0
    assert result["debug"]["memory_written"]["scheduled"] is False
    assert unanswered["answer_status"] == "pending_quarantined_answer"
