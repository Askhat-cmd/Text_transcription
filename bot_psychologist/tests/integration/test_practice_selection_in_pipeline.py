from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier
from bot_agent.practice_selector import practice_selector
from bot_agent.route_resolver import route_resolver


def test_practice_selection_pipeline_contract() -> None:
    diagnostics = diagnostics_classifier.sanitize(
        {
            "interaction_mode": "coaching",
            "nervous_system_state": "window",
            "request_function": "directive",
            "core_theme": "прокрастинация и вина",
            "confidence": {
                "interaction_mode": 0.8,
                "nervous_system_state": 0.8,
                "request_function": 0.8,
                "core_theme": 0.7,
            },
        }
    )
    route = route_resolver.resolve(
        diagnostics,
        safety_override=False,
        practice_candidate_score=0.8,
    )
    selection = practice_selector.select(
        route=route.route,
        nervous_system_state=diagnostics.nervous_system_state,
        request_function=diagnostics.request_function,
        core_theme=diagnostics.core_theme,
    )
    assert route.route in {"practice", "reflect", "regulate", "contact_hold", "inform", "safe_override"}
    if route.route in {"practice", "regulate", "reflect", "contact_hold"}:
        assert selection.primary is not None

