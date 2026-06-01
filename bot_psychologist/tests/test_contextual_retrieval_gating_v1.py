from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.dialogue_pragmatics import build_contextual_retrieval_decision_v1


def _hit(chunk_id: str, content: str, score: float = 0.9) -> SemanticHit:
    return SemanticHit(
        chunk_id=chunk_id,
        content=content,
        source="kb",
        score=score,
    )


def test_example_followup_can_include_kb_grounding() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={
            "is_contextual_followup": True,
            "previous_assistant_offer_type": "example",
            "inherited_topic": "нейросталкинг",
        },
        knowledge_answer_guard={"knowledge_answer": {"needed": True}},
        semantic_hits=[_hit("c1", "Нейросталкинг — наблюдение паттернов.")],
    )
    assert decision["retrieval_action"] in {"kb_grounding", "concept_answer"}
    assert decision["rag_included_count"] >= 1
    assert decision["writer_can_ignore_rag"] is True


def test_phrase_followup_prefers_recent_context_without_rag_dump() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={
            "is_contextual_followup": True,
            "previous_assistant_offer_type": "short_phrase",
        },
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
        semantic_hits=[_hit("c1", "Шумный нерелевантный чанк", score=0.51)],
    )
    assert decision["retrieval_action"] == "recent_context_only"
    assert decision["rag_included_count"] == 0
    assert decision["rag_suppressed_reason"] != ""


def test_no_blanket_short_message_suppression_when_knowledge_needed() -> None:
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics={
            "is_contextual_followup": False,
            "previous_assistant_offer_type": "unknown",
        },
        knowledge_answer_guard={"knowledge_answer": {"needed": True}},
        semantic_hits=[_hit("c1", "Контекст по концепту")],
    )
    assert decision["retrieval_action"] in {"concept_answer", "kb_grounding", "memory_only"}
