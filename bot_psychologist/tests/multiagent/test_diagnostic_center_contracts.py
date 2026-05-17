from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_v1 import (
    DiagnosticCenterInput,
    DiagnosticCenterOutput,
)
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def test_contract_roundtrip_and_required_fields() -> None:
    payload = DiagnosticCenterInput(
        user_message="test message",
        nervous_state="window",
        intent="explore",
        openness="open",
        ok_position="I+W+",
        relation_to_thread="continue",
        phase="clarify",
        safety_flag=False,
        response_mode="reflect",
        pattern_core="core",
        knowledge_hits=[{"lens_family": "insufficient_self", "score": 0.9}],
    )
    output = build_diagnostic_center_output_v1(payload)
    as_dict = output.to_dict()
    restored = DiagnosticCenterOutput.from_dict(as_dict)
    restored_dict = restored.to_dict()

    for key in [
        "schema_version",
        "status",
        "working_hypothesis",
        "next_micro_shift",
        "trace",
        "diagnostic_center_runtime_enabled",
        "user_facing_text_generated",
    ]:
        assert key in restored_dict
    assert restored_dict["diagnostic_center_runtime_enabled"] is False
    assert restored_dict["user_facing_text_generated"] is False


def test_input_unknown_normalization_does_not_break_contract() -> None:
    payload = DiagnosticCenterInput(
        user_message="x",
        nervous_state="bad",
        intent="bad",
        openness="bad",
        ok_position="bad",
        relation_to_thread="bad",
        phase="bad",
    )
    output = build_diagnostic_center_output_v1(payload)
    data = output.to_dict()
    assert data["nervous_state"] == "unknown"
    assert data["intent"] == "unknown"
    assert data["openness"] == "unknown"
    assert data["ok_position"] == "unknown"
