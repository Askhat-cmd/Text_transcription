from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def _build(nervous_state: str, intent: str, safety_flag: bool = False) -> dict:
    payload = DiagnosticCenterInput(
        user_message="unsafe overload",
        nervous_state=nervous_state,
        intent=intent,
        openness="defensive",
        ok_position="I-W+",
        relation_to_thread="continue",
        phase="stabilize",
        safety_flag=safety_flag,
        response_mode="regulate",
    )
    return build_diagnostic_center_output_v1(payload).to_dict()


def test_hyper_forces_safety_first_and_low_depth() -> None:
    out = _build("hyper", "directive")
    assert out["status"] == "safety_first"
    assert out["next_micro_shift"]["depth_allowed"] in {"none", "low"}
    assert out["next_micro_shift"]["max_questions"] <= 1


def test_hypo_forces_safety_first_and_no_deep_analysis() -> None:
    out = _build("hypo", "contact")
    assert out["status"] == "safety_first"
    assert "deep_analysis" in out["next_micro_shift"]["must_not_do"]


def test_crisis_intent_forces_safety_first() -> None:
    out = _build("window", "crisis")
    assert out["status"] == "safety_first"
