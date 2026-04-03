from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_mixed_query_not_reduced_to_glossary(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(interaction_mode=mode, request_function="understand")

    harness = setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
        answer_text=(
            "Понял запрос: сначала объясню идею, затем свяжу её с твоим опытом. "
            "Так ты получишь не только определение, но и практический угол применения."
        ),
    )

    result = adaptive.answer_question_adaptive(
        query="Объясни избегание и почему мне кажется, что это про меня",
        user_id="golden_mixed_not_glossary",
        debug=True,
    )

    assert result["metadata"]["informational_mode"] is False
    assert result["metadata"]["resolved_route"] != "inform"
    assert result["debug_trace"]["phase8_signals"]["mixed_query"] is True

    kwargs = harness.llm_capture.get("kwargs", {})
    assert kwargs.get("mode") != "CLARIFICATION"
