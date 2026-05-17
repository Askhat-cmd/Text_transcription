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


def test_safety_case_tightens_depth_and_questions() -> None:
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

    replay = build_writer_prompt_replay_v1(
        writer_contract=writer_contract,
        writer_contract_pilot={
            "overlay": {
                "candidate_constraints": {
                    "depth_limit": "low",
                    "max_questions": 0,
                    "max_concepts": 1,
                    "must_do": [],
                    "must_not_do": ["do_not_analyze_deeply"],
                    "kb_usage_mode": "none",
                },
                "risk_assessment": {"activation_readiness": "not_ready"},
            }
        },
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()

    assert replay["quality"]["safety_ok"] is True
    assert replay["quality"]["quality_status"] in {"needs_review", "passed"}
