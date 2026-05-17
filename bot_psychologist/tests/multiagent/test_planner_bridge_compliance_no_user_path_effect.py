from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1
from bot_agent.multiagent.planner_bridge_compliance_shadow import (
    build_planner_bridge_compliance_runtime_shadow_v1,
)


def test_runtime_shadow_payload_keeps_no_user_path_effect() -> None:
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
    ).to_dict()
    payload = build_planner_bridge_compliance_runtime_shadow_v1(
        diagnostic_center_shadow={
            "status": "ok",
            "output": output,
            "divergence": {"kb_boundary_ok": True, "raw_kb_text_exposed": False, "warnings": []},
        },
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
    )
    compliance = payload["planner_bridge_compliance_shadow"]
    assert compliance["activation_mode"] == "shadow_compare_only"
    assert compliance["apply_to_writer"] is False
    assert compliance["apply_to_writer_contract"] is False
    assert compliance["writer_prompt_changed"] is False
    assert compliance["final_answer_changed"] is False

