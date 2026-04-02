from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_full_pipeline_window_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="understand",
            core_theme="self_reflection",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Хочу понять, почему застреваю в повторяющемся сценарии.",
        user_id="e2e_window",
        diagnostics_builder=_diagnostics,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["resolved_route"] == "reflect"

