from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier


def test_diagnostics_sanitize_applies_safe_defaults_on_invalid_payload() -> None:
    payload = {
        "interaction_mode": "unknown",
        "nervous_system_state": "invalid",
        "request_function": "other",
        "core_theme": "",
        "confidence": {
            "interaction_mode": "bad",
            "nervous_system_state": 10,
            "request_function": -2,
            "core_theme": None,
        },
        "optional": {"readiness_markers": "not-a-list"},
    }
    result = diagnostics_classifier.sanitize(payload)
    normalized = result.as_dict()

    assert normalized["interaction_mode"] == "coaching"
    assert normalized["nervous_system_state"] == "window"
    assert normalized["request_function"] == "understand"
    assert normalized["core_theme"] == "unspecified_current_issue"
    assert 0.0 <= normalized["confidence"]["interaction_mode"] <= 1.0
    assert 0.0 <= normalized["confidence"]["nervous_system_state"] <= 1.0
    assert 0.0 <= normalized["confidence"]["request_function"] <= 1.0
    assert 0.0 <= normalized["confidence"]["core_theme"] <= 1.0
    assert normalized["optional"]["readiness_markers"] == []


def test_diagnostics_default_contract_is_runtime_safe() -> None:
    default = diagnostics_classifier.default().as_dict()
    assert default["interaction_mode"] == "coaching"
    assert default["nervous_system_state"] == "window"
    assert default["request_function"] == "understand"
    assert default["core_theme"] == "unspecified_current_issue"
