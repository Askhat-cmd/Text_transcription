from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_mixed_query_adds_bridge_instruction(monkeypatch) -> None:
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
        query="Объясни нейросталкинг и почему у меня это не получается в жизни?",
        user_id="phase8_mixed",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace["phase8_signals"]["mixed_query"] is True
    assert "MIXED_QUERY_POLICY" in (trace.get("phase8_context_suffix") or "")
