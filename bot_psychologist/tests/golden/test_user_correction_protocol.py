from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_user_correction_protocol_recalibrates_diagnostics(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        return build_diagnostics(
            interaction_mode="coaching",
            request_function="understand",
            interaction_conf=0.91,
            request_conf=0.92,
        )

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=3,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
    )

    result = adaptive.answer_question_adaptive(
        query="Нет, не то, я не об этом.",
        user_id="phase8_correction",
        debug=True,
    )

    assert result["status"] == "success"
    diagnostics = result["metadata"]["diagnostics_v1"]
    assert diagnostics["request_function"] == "validation"
    assert diagnostics["confidence"]["request_function"] <= 0.61
    assert result["debug_trace"]["user_correction_protocol"] is True
    assert "USER_CORRECTION_PROTOCOL" in (result["debug_trace"].get("phase8_context_suffix") or "")
