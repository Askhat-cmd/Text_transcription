from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_full_pipeline_hypo_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="hypo",
            request_function="contact",
            core_theme="apathy",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Я как будто выключен и вообще не чувствую энергии.",
        user_id="e2e_hypo",
        diagnostics_builder=_diagnostics,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["resolved_route"] == "regulate"

