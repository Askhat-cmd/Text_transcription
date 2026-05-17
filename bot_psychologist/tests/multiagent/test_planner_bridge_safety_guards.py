from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.planner_bridge_candidate import build_planner_bridge_candidate_v1
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def test_safety_context_forces_limited_low_depth() -> None:
    output = build_diagnostic_center_output_v1(
        DiagnosticCenterInput(
            user_message="очень тревожно",
            nervous_state="hyper",
            intent="contact",
            openness="defensive",
            ok_position="I-W+",
            relation_to_thread="continue",
            phase="stabilize",
            safety_flag=True,
            response_mode="safe_override",
            pattern_core="acute",
        )
    )
    bridge = build_planner_bridge_candidate_v1(
        diagnostic_center_output=output,
        divergence={"kb_boundary_ok": True, "raw_kb_text_exposed": False, "warnings": [], "hard_blocker_reasons": []},
        divergence_severity="expected_divergence",
        diagnostic_card=DiagnosticCard(
            version="diagnostic_card_v1",
            situation_label="safety",
            user_state_summary="safety",
            thread_line_summary="safety",
            current_need="regulate",
            suggested_writer_move="safe_override",
            confidence=0.9,
            trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
        ),
        thread_state=ThreadState(
            thread_id="t1",
            user_id="u1",
            core_direction="d1",
            phase="stabilize",
            relation_to_thread="continue",
            response_mode="safe_override",
            response_goal="ground",
            openness="defensive",
            ok_position="I-W+",
            pattern_core="acute",
            safety_active=True,
        ),
        state_snapshot=StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9),
    ).to_dict()
    assert bridge["status"] == "limited"
    assert bridge["depth_limit"] in {"none", "low"}
    assert bridge["max_questions"] == 0
    assert "safety_first" in bridge["safety_constraints"]
    assert bridge["apply_to_writer"] is False

