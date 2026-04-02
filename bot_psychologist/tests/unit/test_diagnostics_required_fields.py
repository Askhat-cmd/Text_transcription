from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import (
    INTERACTION_MODES,
    NERVOUS_SYSTEM_STATES,
    REQUEST_FUNCTIONS,
    diagnostics_classifier,
)


def test_diagnostics_required_fields_exist_and_valid() -> None:
    result = diagnostics_classifier.classify(
        query="Объясни, что такое когнитивное слияние",
        state_analysis=None,
        informational_mode_hint=True,
    )
    payload = result.as_dict()

    assert set(payload.keys()) == {
        "interaction_mode",
        "nervous_system_state",
        "request_function",
        "core_theme",
        "confidence",
        "optional",
    }
    assert payload["interaction_mode"] in INTERACTION_MODES
    assert payload["nervous_system_state"] in NERVOUS_SYSTEM_STATES
    assert payload["request_function"] in REQUEST_FUNCTIONS
    assert isinstance(payload["core_theme"], str) and payload["core_theme"]
    assert set(payload["confidence"].keys()) == {
        "interaction_mode",
        "nervous_system_state",
        "request_function",
        "core_theme",
    }
