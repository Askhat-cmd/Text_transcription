from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_mixed_query_richness_runtime(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(
            interaction_mode=mode,
            nervous_system_state="window",
            request_function="understand",
            core_theme="mixed_query",
        )

    result, harness = run_adaptive_case(
        monkeypatch,
        query="Объясни избегание и как это увидеть у себя в реальной жизни",
        user_id="e2e_103_mixed_rich",
        diagnostics_builder=_diagnostics,
        answer_text=(
            "Избегание — это способ снизить напряжение, но цена часто в сужении выбора. "
            "У себя это видно в повторяющемся откладывании и внутреннем оправдании. "
            "Практический ракурс: заметить триггер, телесную реакцию и первый импульс ухода."
        ),
    )

    assert result["status"] == "success"
    assert result["metadata"]["resolved_route"] != "inform"
    assert result["metadata"]["informational_mode"] is False
    assert result["debug_trace"]["phase8_signals"]["mixed_query"] is True
    assert "MIXED_QUERY_POLICY" in (result["debug_trace"].get("phase8_context_suffix") or "")
    assert harness.llm_capture.get("kwargs", {}).get("mode") != "CLARIFICATION"
