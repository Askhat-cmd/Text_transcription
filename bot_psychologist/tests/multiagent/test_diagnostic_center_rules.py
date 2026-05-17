from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def _build(ok_position: str, openness: str, intent: str = "explore") -> dict:
    payload = DiagnosticCenterInput(
        user_message="rule check",
        nervous_state="window",
        intent=intent,
        openness=openness,
        ok_position=ok_position,
        relation_to_thread="continue",
        phase="clarify",
        safety_flag=False,
        response_mode="reflect",
    )
    return build_diagnostic_center_output_v1(payload).to_dict()


def test_i_minus_w_plus_defensive_stabilize_authorship() -> None:
    out = _build("I-W+", "defensive", intent="directive")
    assert out["next_micro_shift"]["response_goal"] == "stabilize_authorship"
    assert "give_directive_certainty" in out["next_micro_shift"]["must_not_do"]


def test_i_plus_w_minus_defensive_decenter_without_shaming() -> None:
    out = _build("I+W-", "defensive")
    assert out["next_micro_shift"]["response_goal"] == "decenter_without_shaming"
    assert "join_accusation" in out["next_micro_shift"]["must_not_do"]


def test_i_plus_w_plus_open_allows_deeper_mode() -> None:
    out = _build("I+W+", "open")
    assert out["next_micro_shift"]["response_goal"] == "deepen_and_integrate"
    assert out["next_micro_shift"]["depth_allowed"] == "medium|high"
