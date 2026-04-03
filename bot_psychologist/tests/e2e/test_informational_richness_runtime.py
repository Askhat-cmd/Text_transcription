from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_informational_richness_runtime(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(
            interaction_mode=mode,
            nervous_system_state="window",
            request_function="understand",
            core_theme="difference",
        )

    result, harness = run_adaptive_case(
        monkeypatch,
        query="Объясни, что такое самоосознание и чем оно отличается от самонаблюдения",
        user_id="e2e_103_inform_rich",
        diagnostics_builder=_diagnostics,
        answer_text=(
            "Самоосознание и самонаблюдение связаны, но не равны: первое про позицию субъекта, второе про фиксацию процессов. "
            "В реальном опыте разница видна по тому, кто управляет вниманием и выбором действия."
        ),
    )

    assert result["status"] == "success"
    assert result["metadata"]["resolved_route"] == "inform"
    assert result["metadata"]["informational_mode"] is True
    assert result["metadata"]["applied_mode_prompt"] == "prompt_mode_informational"
    assert harness.llm_capture.get("kwargs", {}).get("mode") == "CLARIFICATION"
