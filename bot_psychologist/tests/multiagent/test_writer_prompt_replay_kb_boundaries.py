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
from bot_agent.multiagent.writer_prompt_replay import build_writer_prompt_replay_v1


def test_kb_forbidden_fields_are_blocked_and_normalized() -> None:
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
        situation_label="kb",
        user_state_summary="kb",
        thread_line_summary="kb",
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

    replay = build_writer_prompt_replay_v1(
        writer_contract=writer_contract,
        writer_contract_pilot={
            "overlay": {
                "candidate_constraints": {
                    "kb_usage_mode": "raw_text",
                    "must_not_quote_source": False,
                    "must_do": [],
                    "must_not_do": [],
                },
                "risk_assessment": {"activation_readiness": "pilot_ready"},
            }
        },
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()

    assert replay["candidate_summary"]["has_forbidden_kb_fields"] is False
    assert replay["quality"]["kb_boundary_ok"] is True
