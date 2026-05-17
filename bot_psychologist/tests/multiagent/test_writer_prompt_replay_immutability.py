from __future__ import annotations

import hashlib
import json
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


def _h(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def test_writer_prompt_replay_keeps_writer_contract_immutable() -> None:
    state = StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8)
    thread = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="d1",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        response_goal="clarify",
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

    before = _h(writer_contract.to_dict())
    replay = build_writer_prompt_replay_v1(
        writer_contract=writer_contract,
        writer_contract_pilot={"overlay": {"candidate_constraints": {}, "risk_assessment": {"activation_readiness": "pilot_ready"}}},
        diagnostic_card=card,
        thread_state=thread,
        state_snapshot=state,
    ).to_dict()
    after = _h(writer_contract.to_dict())

    assert before == after
    assert replay["quality"]["non_mutating_ok"] is True
