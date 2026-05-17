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


def test_kb_boundary_violation_results_in_blocked_status() -> None:
    card = DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="kb",
        user_state_summary="kb",
        thread_line_summary="kb",
        current_need="clarify",
        suggested_writer_move="clarify_one_point",
        confidence=0.8,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )
    state = StateSnapshot("window", "clarify", "mixed", "I-W+", False, 0.8)
    thread = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="d1",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        response_goal="clarify",
        openness="mixed",
        ok_position="I-W+",
        pattern_core="kb_block",
    )
    output = build_diagnostic_center_output_v1(
        DiagnosticCenterInput(
            user_message="kb",
            nervous_state="window",
            intent="clarify",
            openness="mixed",
            ok_position="I-W+",
            relation_to_thread="continue",
            phase="clarify",
            response_mode="reflect",
            pattern_core="kb_block",
        )
    )
    bridge = build_planner_bridge_candidate_v1(
        diagnostic_center_output=output,
        divergence={
            "kb_boundary_ok": False,
            "raw_kb_text_exposed": True,
            "hard_blocker_reasons": ["kb_boundary_violation"],
        },
        divergence_severity="hard_blocker",
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    )
    compliance = build_planner_bridge_compliance_shadow_v1(
        writer_move_instructions=build_writer_move_instructions_v1(card),
        planner_bridge_output=bridge,
        diagnostic_card=card,
        divergence={"kb_boundary_ok": False, "raw_kb_text_exposed": True},
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()
    assert compliance["compatibility"]["overall_status"] == "blocked"
    assert compliance["compatibility"]["kb_boundary_compatible"] is False
    assert "kb_boundary_violation" in compliance["blocked_reasons"]

