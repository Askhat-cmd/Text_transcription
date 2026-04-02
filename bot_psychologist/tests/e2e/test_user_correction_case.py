from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_user_correction_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="understand",
            core_theme="recalibration",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Нет, не то, я про страх ошибки перед публичным выступлением.",
        user_id="e2e_user_correction",
        diagnostics_builder=_diagnostics,
        turns_count=2,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["user_correction_protocol"] is True
    assert result["debug_trace"]["diagnostics_v1"]["request_function"] == "validation"

