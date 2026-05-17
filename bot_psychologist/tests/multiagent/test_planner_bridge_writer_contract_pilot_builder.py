from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.context_package import ContextAssemblyPackage
from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard, DiagnosticCardTrace
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.planner_bridge_writer_contract_pilot import (
    build_planner_bridge_writer_contract_pilot_v1,
)


def test_writer_contract_pilot_builder_returns_shadow_only_overlay() -> None:
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
        pattern_core="core",
    )
    card = DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="test",
        user_state_summary="test",
        thread_line_summary="test",
        current_need="clarify",
        suggested_writer_move="clarify_one_point",
        confidence=0.8,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )
    writer_contract = WriterContract(
        user_message="test",
        thread_state=thread,
        memory_bundle=MemoryBundle(conversation_context="ctx", has_relevant_knowledge=False, context_turns=1),
        context_package=ContextAssemblyPackage(current_user_message="test"),
        diagnostic_card=card,
    )
    pilot = build_planner_bridge_writer_contract_pilot_v1(
        writer_contract=writer_contract,
        planner_bridge_compliance_shadow={
            "compatibility": {"overall_status": "tightens_constraints", "kb_boundary_compatible": True},
            "planner_bridge_candidate": {
                "response_goal_candidate": "clarify",
                "response_mode_candidate": "reflect",
                "depth_limit": "low_to_medium",
                "max_questions": 1,
                "max_concepts": 1,
                "must_do_candidates": ["reflect_one_key_point"],
                "must_not_do_candidates": ["do_not_open_multiple_threads"],
                "kb_constraints": {"kb_usage_mode": "internal_lens_only", "must_not_quote_source": True},
            },
        },
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()

    overlay = pilot["overlay"]
    assert overlay["activation_mode"] == "pilot_shadow_only"
    assert overlay["apply_to_writer_contract"] is False
    assert overlay["apply_to_writer_prompt"] is False
    assert overlay["apply_to_final_answer"] is False
    assert overlay["merge_policy"]["mode"] == "non_mutating_compare_only"
    assert overlay["guardrails"]["provider_called"] is False
