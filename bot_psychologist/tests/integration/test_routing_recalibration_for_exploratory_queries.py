from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_routing_recalibration_for_exploratory_mixed_query(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(interaction_mode=mode, request_function="understand")

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
    )

    result = adaptive.answer_question_adaptive(
        query="Объясни, что такое избегание, потому что кажется это про меня",
        user_id="phase103_mixed",
        debug=True,
    )

    assert result["metadata"]["informational_mode"] is False
    assert result["metadata"]["resolved_route"] != "inform"


def test_routing_recalibration_keeps_pure_definition_in_inform(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(interaction_mode=mode, request_function="understand")

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
    )

    result = adaptive.answer_question_adaptive(
        query="Объясни, что такое избегание",
        user_id="phase103_inform",
        debug=True,
    )

    assert result["metadata"]["informational_mode"] is True
    assert result["metadata"]["resolved_route"] == "inform"
