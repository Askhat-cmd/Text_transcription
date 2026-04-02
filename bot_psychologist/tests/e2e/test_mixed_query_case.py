from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_mixed_query_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="informational",
            nervous_system_state="window",
            request_function="understand",
            core_theme="mixed_query",
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Объясни, что такое самонаблюдение, и как мне это применять в моем конфликте.",
        user_id="e2e_mixed_query",
        diagnostics_builder=_diagnostics,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["resolved_route"] == "inform"
    assert bool(result["debug_trace"].get("phase8_context_suffix"))

