from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier


def test_diagnostics_schema_v101_contract_shape() -> None:
    payload = diagnostics_classifier.classify(
        query="Я запутался и хочу понять, что со мной происходит",
        state_analysis=None,
        informational_mode_hint=False,
    ).as_dict()

    assert isinstance(payload, dict)
    assert isinstance(payload["interaction_mode"], str)
    assert isinstance(payload["nervous_system_state"], str)
    assert isinstance(payload["request_function"], str)
    assert isinstance(payload["core_theme"], str)
    assert isinstance(payload["confidence"], dict)
    assert isinstance(payload["optional"], dict)

    for key in ("interaction_mode", "nervous_system_state", "request_function", "core_theme"):
        assert key in payload["confidence"]
        value = payload["confidence"][key]
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0
