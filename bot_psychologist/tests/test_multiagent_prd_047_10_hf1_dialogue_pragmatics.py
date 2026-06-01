from __future__ import annotations

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread_state() -> ThreadState:
    return ThreadState(
        thread_id="prd04710hf1-test",
        user_id="u-test",
        phase="clarify",
        response_mode="reflect",
        core_direction="",
    )


def test_writer_contract_includes_dialogue_pragmatics_and_retrieval_decision() -> None:
    contract = WriterContract(
        user_message="да",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(
            semantic_hits=[
                SemanticHit(chunk_id="c1", content="candidate one", source="kb", score=0.8),
                SemanticHit(chunk_id="c2", content="candidate two", source="kb", score=0.7),
            ]
        ),
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={
            "version": "dialogue_pragmatics_v1",
            "is_contextual_followup": True,
            "previous_assistant_offer_type": "short_phrase",
            "should_answer_directly": True,
        },
        retrieval_decision={
            "retrieval_decision_version": "contextual_retrieval_gating_v1",
            "retrieval_action": "recent_context_only",
            "rag_candidates_count": 2,
            "rag_included_count": 0,
            "writer_can_ignore_rag": True,
            "rag_included_for_writer": [],
        },
    )
    ctx = contract.to_prompt_context()
    assert ctx["dialogue_pragmatics_is_contextual_followup"] is True
    assert ctx["dialogue_pragmatics_offer_type"] == "short_phrase"
    assert ctx["retrieval_action"] == "recent_context_only"
    assert ctx["retrieval_rag_candidates_count"] == 2
    assert ctx["semantic_hits"] == []


def test_writer_compliance_rewrites_regulate_stub_on_contextual_followup() -> None:
    writer = WriterAgent(client=object(), model="gpt-5-mini")
    contract = WriterContract(
        user_message="да предложи",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(),
        response_planner={
            "next_move": "continue_active_line",
            "answer_shape": "compact_direct",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={
            "version": "dialogue_pragmatics_v1",
            "is_contextual_followup": True,
            "previous_assistant_offer_type": "short_phrase",
            "should_not_ask_confirmation_again": True,
            "should_answer_directly": True,
        },
    )
    fixed = writer._enforce_answer_compliance(
        "Сфокусируюсь на разборе, без практик по умолчанию.",
        contract,
    )
    lowered = fixed.lower()
    assert "сфокусируюсь на разборе" not in lowered
    assert "фраза" in lowered
