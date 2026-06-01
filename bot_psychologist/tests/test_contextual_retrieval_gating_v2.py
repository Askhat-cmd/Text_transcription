from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.dialogue_pragmatics import build_contextual_retrieval_decision_v1


def _hit(chunk_id: str, content: str) -> SemanticHit:
    return SemanticHit(chunk_id=chunk_id, content=content, source="kb", score=0.9)


def test_close_ack_turn_prefers_none() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={"short_utterance_type": "close_ack"},
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
        semantic_hits=[_hit("c1", "context")],
    )
    assert decision["retrieval_action"] == "none"
    assert decision["rag_included_count"] == 0


def test_practice_overview_uses_practice_catalog() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={"is_contextual_followup": False},
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "answer_type": "practice_overview"}},
        semantic_hits=[_hit("c1", "practice one"), _hit("c2", "practice two")],
    )
    assert decision["retrieval_action"] == "practice_catalog"
    assert decision["rag_included_count"] >= 1


def test_memory_only_has_zero_included_rag() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={"is_contextual_followup": False, "previous_assistant_offer_type": "unknown"},
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
        semantic_hits=[_hit("c3", "optional candidate")],
    )
    if decision["retrieval_action"] == "memory_only":
        assert decision["rag_included_count"] == 0
