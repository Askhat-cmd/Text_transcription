from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import setup_phase8_runtime


def test_runtime_generic_rasskazhi_does_not_fall_into_inform(monkeypatch) -> None:
    real_diagnostics = adaptive.diagnostics_classifier.classify

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=lambda query, state_analysis, informational_mode_hint=False: real_diagnostics(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
        ),
    )

    result = adaptive.answer_question_adaptive(
        query="Расскажи о системе нейросталкинга",
        user_id="phase1031_runtime_rasskazhi",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["metadata"]["informational_mode"] is False
    assert result["metadata"]["resolved_route"] != "inform"


def test_runtime_definition_query_still_goes_inform(monkeypatch) -> None:
    real_diagnostics = adaptive.diagnostics_classifier.classify

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=lambda query, state_analysis, informational_mode_hint=False: real_diagnostics(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
        ),
    )

    result = adaptive.answer_question_adaptive(
        query="Что такое нейросталкинг?",
        user_id="phase1031_runtime_definition",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["metadata"]["informational_mode"] is True
    assert result["metadata"]["resolved_route"] == "inform"


def test_runtime_practice_entry_query_does_not_fall_into_inform(monkeypatch) -> None:
    real_diagnostics = adaptive.diagnostics_classifier.classify

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=lambda query, state_analysis, informational_mode_hint=False: real_diagnostics(
            query=query,
            state_analysis=state_analysis,
            informational_mode_hint=informational_mode_hint,
        ),
    )

    result = adaptive.answer_question_adaptive(
        query="Объясни, что такое избегание и как начать это практиковать",
        user_id="phase1031_runtime_practice",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["metadata"]["informational_mode"] is False
    assert result["metadata"]["resolved_route"] != "inform"

