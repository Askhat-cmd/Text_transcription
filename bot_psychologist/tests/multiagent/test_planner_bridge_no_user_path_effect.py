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


def test_bridge_is_always_shadow_only_no_writer_apply() -> None:
    output = build_diagnostic_center_output_v1(
        DiagnosticCenterInput(
            user_message="test",
            nervous_state="window",
            intent="clarify",
            openness="mixed",
            ok_position="I-W+",
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
            "user_path": {
                "writer_contract_changed": False,
                "writer_prompt_changed_by_shadow": False,
                "final_answer_changed_by_shadow": False,
                "diagnostic_center_output_passed_to_writer": False,
            },
        },
        divergence_severity="compatible",
        diagnostic_card=DiagnosticCard(
            version="diagnostic_card_v1",
            situation_label="test",
            user_state_summary="test",
            thread_line_summary="test",
            current_need="clarify",
            suggested_writer_move="clarify_one_point",
            confidence=0.8,
            trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
        ),
        thread_state=ThreadState(
            thread_id="t1",
            user_id="u1",
            core_direction="d1",
            phase="clarify",
            relation_to_thread="continue",
            response_mode="reflect",
            response_goal="clarify",
            openness="mixed",
            ok_position="I-W+",
            pattern_core="core",
        ),
        state_snapshot=StateSnapshot("window", "clarify", "mixed", "I-W+", False, 0.8),
    ).to_dict()
    assert bridge["activation_mode"] == "shadow_only"
    assert bridge["apply_to_writer"] is False
    assert bridge["apply_to_writer_contract"] is False
    assert bridge["guardrails"]["user_path_effect"] == "none"

