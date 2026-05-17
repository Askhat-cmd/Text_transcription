from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1
from bot_agent.multiagent.planner_bridge_candidate import build_planner_bridge_candidate_v1
from bot_agent.multiagent.planner_bridge_compliance_shadow import (
    build_planner_bridge_compliance_shadow_v1,
)
from bot_agent.multiagent.writer_move_compliance import build_writer_move_instructions_v1


def test_safety_case_is_marked_safety_compatible() -> None:
    card = DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="safety",
        user_state_summary="safety",
        thread_line_summary="safety",
        current_need="regulate",
        suggested_writer_move="safe_override",
        confidence=0.9,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )
    state = StateSnapshot("hyper", "contact", "defensive", "I-W+", True, 0.9)
    thread = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="d1",
        phase="stabilize",
        relation_to_thread="continue",
        response_mode="safe_override",
        response_goal="safety",
        openness="defensive",
        ok_position="I-W+",
        pattern_core="acute",
        safety_active=True,
    )
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
        divergence={"kb_boundary_ok": True, "raw_kb_text_exposed": False, "hard_blocker_reasons": []},
        divergence_severity="expected_divergence",
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    )
    compliance = build_planner_bridge_compliance_shadow_v1(
        writer_move_instructions=build_writer_move_instructions_v1(card),
        planner_bridge_output=bridge,
        diagnostic_card=card,
        divergence={"kb_boundary_ok": True, "raw_kb_text_exposed": False},
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()
    assert compliance["compatibility"]["safety_compatible"] is True
    assert compliance["compatibility"]["overall_status"] in {
        "expected_divergence",
        "tightens_constraints",
        "compatible",
    }

