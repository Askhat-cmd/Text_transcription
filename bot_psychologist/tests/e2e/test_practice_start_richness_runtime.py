from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_practice_start_richness_runtime(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(
            interaction_mode=mode,
            nervous_system_state="window",
            request_function="directive",
            core_theme="practice_start",
        )

    result, harness = run_adaptive_case(
        monkeypatch,
        query="Как начать это практиковать без перегруза?",
        user_id="e2e_103_practice_start",
        diagnostics_builder=_diagnostics,
        answer_text=(
            "Начни с короткого входа на 5 минут: сначала отмечай триггер, затем телесную реакцию и только потом действие. "
            "Так ты формируешь наблюдение без давления и не превращаешь практику в ещё одну обязанность."
        ),
    )

    assert result["status"] == "success"
    assert result["metadata"]["resolved_route"] != "inform"
    assert result["metadata"]["informational_mode"] is False
    assert harness.llm_capture.get("kwargs", {}).get("mode") != "CLARIFICATION"
