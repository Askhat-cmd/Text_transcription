from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_first_turn_richness_runtime(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(
            interaction_mode=mode,
            nervous_system_state="window",
            request_function="explore",
            core_theme="first_turn",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Привет, помоги понять что со мной происходит",
        user_id="e2e_103_first_turn",
        diagnostics_builder=_diagnostics,
        turns_count=0,
        answer_text=(
            "Сейчас ты описываешь состояние неопределенности, где важно вернуть опору и ясность. "
            "Можно начать с наблюдения: что запускает напряжение и как тело реагирует в первые минуты."
        ),
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["phase8_signals"]["first_turn"] is True
    suffix = result["debug_trace"].get("phase8_context_suffix") or ""
    assert "FIRST_TURN_POLICY" in suffix
    assert "полноценный первый смысловой каркас" in suffix
