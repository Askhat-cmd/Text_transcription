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


def _diagnostic_card() -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="test",
        user_state_summary="test",
        thread_line_summary="test",
        current_need="clarify",
        suggested_writer_move="clarify_one_point",
        avoid_list=["give_final_advice", "give_final_advice"],
        confidence=0.8,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="d1",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        response_goal="clarify",
        must_avoid=["quote_kb_directly", "quote_kb_directly"],
        openness="open",
        ok_position="I+W+",
        pattern_core="core",
    )


def _state() -> StateSnapshot:
    return StateSnapshot("window", "explore", "open", "I+W+", False, 0.8)


def test_planner_bridge_builder_candidate_and_bounded_lists() -> None:
    output = build_diagnostic_center_output_v1(
        DiagnosticCenterInput(
            user_message="test",
            nervous_state="window",
            intent="explore",
            openness="open",
            ok_position="I+W+",
            relation_to_thread="continue",
            phase="clarify",
            response_mode="reflect",
            pattern_core="core",
        )
    )
    bridge = build_planner_bridge_candidate_v1(
        diagnostic_center_output=output,
        divergence={
            "kb_boundary_ok": True,
            "raw_kb_text_exposed": False,
            "warnings": [],
            "hard_blocker_reasons": [],
            "expected_divergence": False,
        },
        divergence_severity="compatible",
        diagnostic_card=_diagnostic_card(),
        thread_state=_thread(),
        state_snapshot=_state(),
    ).to_dict()
    assert bridge["status"] == "candidate"
    assert bridge["activation_mode"] == "shadow_only"
    assert bridge["apply_to_writer"] is False
    assert bridge["apply_to_writer_contract"] is False
    assert len(bridge["must_do_candidates"]) <= 6
    assert len(bridge["must_not_do_candidates"]) <= 8
    assert bridge["kb_constraints"]["must_not_quote_source"] is True

