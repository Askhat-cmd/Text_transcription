from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1


class _FakeClient:
    pass


def _contract(*, message: str, dialogue_policy: dict | None = None) -> WriterContract:
    contract = WriterContract(
        user_message=message,
        thread_state=ThreadState(
            thread_id="th_no_stub",
            user_id="u_no_stub",
            core_direction="no stub repair",
            phase="clarify",
            response_mode="reflect",
            response_goal="answer",
            nervous_state="window",
            openness="open",
            ok_position="I+W+",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        memory_bundle=MemoryBundle(conversation_context="", context_turns=0),
    )
    contract.dialogue_policy = dict(dialogue_policy or {})
    return contract


def test_known_concept_repair_returns_original_text_and_sets_retry_signal() -> None:
    agent = WriterAgent(client=_FakeClient(), model="gpt-5-mini")
    original = "Это внешнее слежение и биофидбек. О каком варианте ты говоришь?"
    contract = _contract(
        message="что такое нейросталкинг?",
        dialogue_policy={
            "explicit_answer_need": True,
            "answer_obligation_resolution": {"answer_obligation": "answer_knowledge_question"},
            "knowledge_answer_guard": {
                "needed": True,
                "should_answer_directly": True,
                "concept": "нейросталкинг",
            },
        },
    )

    result = agent._enforce_answer_compliance(original, contract)

    assert result == original
    signal = agent.last_debug["no_stub_repair_signal"]
    assert signal["reason"] == "knowledge_direct_answer_repair"
    assert signal["recommended_action"] == "writer_retry"
    assert signal["user_facing_replacement_created"] is False


def test_gate_converts_no_stub_signal_to_retry_and_quarantine_without_replacement() -> None:
    writer_debug = {
        "no_stub_repair_signal": {
            "version": "no_stub_repair_signal_v1",
            "reason": "knowledge_direct_answer_repair",
            "recommended_action": "writer_retry",
            "must_answer": "known_concept_question",
            "user_facing_replacement_created": False,
        }
    }

    gate = build_final_answer_acceptance_gate_v1(
        user_message="что такое нейросталкинг?",
        final_answer="Это внешнее слежение и биофидбек.",
        dialogue_act_resolution={"dialogue_act": "knowledge_question"},
        answer_obligation_resolution={"answer_obligation": "answer_knowledge_question"},
        unanswered_question_state_before={
            "answer_required": True,
            "last_direct_user_question": "что такое нейросталкинг?",
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": "что такое нейросталкинг?"},
        writer_debug=writer_debug,
        validator_result=SimpleNamespace(is_blocked=False),
    )

    assert gate["status"] == "failed"
    assert "no_stub_repair_signal" in gate["failed_checks"]
    assert gate["retry_recommended"] is True
    assert gate["must_quarantine_answer"] is True
    assert gate["can_save_as_healthy_context"] is False
    assert gate["can_use_as_summary_source"] is False
    assert gate["can_save_last_assistant_offer"] is False
    assert gate["no_stub_repair_signal"]["user_facing_replacement_created"] is False

