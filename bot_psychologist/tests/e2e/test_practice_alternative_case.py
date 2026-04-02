from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_practice_alternative_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="directive",
            core_theme="action_needed",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Дай практику, чтобы выйти из прокрастинации и начать действовать.",
        user_id="e2e_practice_alternative",
        diagnostics_builder=_diagnostics,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["resolved_route"] == "practice"
    assert len(result["debug_trace"]["practice_alternatives"]) <= 2

