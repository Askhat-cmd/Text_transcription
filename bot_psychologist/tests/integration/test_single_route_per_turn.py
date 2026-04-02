from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier
from bot_agent.route_resolver import route_resolver


def test_single_route_per_turn_contract() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Я запутался и хочу понять, как перестать убегать от ответственности",
        state_analysis=None,
    )
    resolution = route_resolver.resolve(diagnostics, safety_override=False)

    # Phase 4 contract: one diagnostics output -> one deterministic route.
    assert isinstance(resolution.route, str)
    assert resolution.route in {
        "safe_override",
        "regulate",
        "reflect",
        "practice",
        "inform",
        "contact_hold",
    }
