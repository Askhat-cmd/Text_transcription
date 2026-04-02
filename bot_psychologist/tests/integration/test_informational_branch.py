from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_informational_branch_resolves_inform_and_skips_practice(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(interaction_mode=mode, request_function="understand")

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
        answer_text="Это объяснение по теме без навязывания практики.",
    )

    result = adaptive.answer_question_adaptive(
        query="Что такое нейросталкинг?",
        user_id="phase8_info",
        debug=True,
    )

    assert result["status"] == "success"
    assert result["metadata"]["resolved_route"] == "inform"
    assert result["metadata"]["informational_mode"] is True
    assert result["metadata"]["selected_practice"] is None
    assert result["metadata"]["recommended_mode"] == "CLARIFICATION"
