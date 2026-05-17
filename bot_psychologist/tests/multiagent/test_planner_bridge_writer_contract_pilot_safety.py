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


def test_safety_case_is_not_ready_and_tightened() -> None:
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
    card = DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="safety",
        user_state_summary="safety",
        thread_line_summary="safety",
        current_need="safety",
        suggested_writer_move="safe_override",
        confidence=0.9,
        trace=DiagnosticCardTrace(version="diagnostic_card_v1", builder="test"),
    )
    writer_contract = WriterContract(
        user_message="Мне тревожно.",
        thread_state=thread,
        memory_bundle=MemoryBundle(conversation_context="ctx", has_relevant_knowledge=False, context_turns=1),
        context_package=ContextAssemblyPackage(current_user_message="test"),
        diagnostic_card=card,
    )

    pilot = build_planner_bridge_writer_contract_pilot_v1(
        writer_contract=writer_contract,
        planner_bridge_compliance_shadow={
            "compatibility": {"overall_status": "expected_divergence", "kb_boundary_compatible": True},
            "planner_bridge_candidate": {
                "depth_limit": "medium",
                "max_questions": 1,
                "max_concepts": 2,
            },
        },
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()

    candidate = pilot["overlay"]["candidate_constraints"]
    risk = pilot["overlay"]["risk_assessment"]
    assert candidate["depth_limit"] in {"none", "low"}
    assert candidate["max_questions"] == 0
    assert candidate["max_concepts"] <= 1
    assert risk["activation_readiness"] in {"not_ready", "blocked"}
