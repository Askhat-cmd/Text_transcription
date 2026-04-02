from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_returning_user_stale_summary_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="explore",
            core_theme="continuity",
        )

    def _runtime_setup(adaptive_module) -> None:
        monkeypatch.setattr(
            adaptive_module.memory_updater,
            "build_runtime_context",
            lambda **_kwargs: SimpleNamespace(
                context=SimpleNamespace(
                    context_text="stale summary context",
                    summary_used=True,
                    staleness="stale",
                    strategy="stale_summary_large_window",
                ),
                snapshot={"schema_version": "1.1"},
            ),
        )

    result, _ = run_adaptive_case(
        monkeypatch,
        query="Продолжим с того места, где я остановился неделю назад.",
        user_id="e2e_stale_summary",
        diagnostics_builder=_diagnostics,
        turns_count=3,
        runtime_setup=_runtime_setup,
    )

    assert result["status"] == "success"
    assert result["debug_trace"]["summary_staleness"] == "stale"
    assert result["debug_trace"]["memory_strategy"] == "stale_summary_large_window"

