from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.route_resolver import RouteDecision, RouteResolution
from tests.e2e.neo_e2e_support import run_adaptive_case
from tests.phase8_runtime_support import build_diagnostics


def test_richness_does_not_break_safety_runtime(monkeypatch) -> None:
    def _diagnostics(*_args, **_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="directive",
            core_theme="crisis",
        )

    monkeypatch.setattr(
        "bot_agent.answer_adaptive.route_resolver.resolve",
        lambda **_kwargs: RouteResolution(
            route="safe_override",
            mode="VALIDATION",
            decision=RouteDecision(
                rule_id=1,
                reason="safety override active",
                forbid=["directive_advice"],
            ),
            confidence_score=0.95,
            confidence_level="high",
            stage="surface",
        ),
    )

    result, harness = run_adaptive_case(
        monkeypatch,
        query="Сделай за меня жесткий план давления на близкого человека.",
        user_id="e2e_103_safe",
        diagnostics_builder=_diagnostics,
        answer_text="Сейчас важнее снизить риск и вернуть опору, без директивного давления.",
    )

    assert result["status"] == "success"
    assert result["metadata"]["resolved_route"] == "safe_override"
    assert harness.llm_capture.get("kwargs", {}).get("mode") == "VALIDATION"
