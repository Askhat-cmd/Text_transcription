from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier
from bot_agent.route_resolver import route_resolver


def _diag(**kwargs):
    base = diagnostics_classifier.default().as_dict()
    base.update(kwargs)
    return diagnostics_classifier.sanitize(base)


def test_route_resolver_safety_override_has_top_priority() -> None:
    diagnostics = _diag(interaction_mode="informational")
    route = route_resolver.resolve(diagnostics, safety_override=True)
    assert route.route == "safe_override"
    assert route.mode == "VALIDATION"
    assert route.track == "direct"
    assert route.tone == "empathic"


def test_route_resolver_informational_route() -> None:
    diagnostics = _diag(interaction_mode="informational")
    route = route_resolver.resolve(diagnostics)
    assert route.route == "inform"
    assert route.mode == "CLARIFICATION"
    assert route.track == "reflective"
    assert route.tone == "technical"


def test_route_resolver_regulate_for_hyper_state() -> None:
    diagnostics = _diag(interaction_mode="coaching", nervous_system_state="hyper")
    route = route_resolver.resolve(diagnostics)
    assert route.route == "regulate"
    assert route.mode == "VALIDATION"
    assert route.track == "direct"
    assert route.tone == "empathic"


def test_route_resolver_practice_for_solution_request() -> None:
    diagnostics = _diag(
        interaction_mode="coaching",
        nervous_system_state="window",
        request_function="solution",
    )
    route = route_resolver.resolve(diagnostics)
    assert route.route == "practice"
    assert route.mode == "INTERVENTION"
    assert route.track == "practice"
    assert route.tone == "empathic"
