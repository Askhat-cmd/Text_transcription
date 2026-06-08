from __future__ import annotations

from bot_agent.multiagent.contextual_retrieval_query_composer import (
    build_contextual_retrieval_query_composer_v1,
    merge_composer_into_retrieval_decision_v1,
)


def test_summary_composer_clears_rag_chunks_in_retrieval_decision() -> None:
    composer = build_contextual_retrieval_query_composer_v1(
        user_message="Подведи итог",
        dialogue_act_resolution={"dialogue_act": "summary_request"},
        answer_obligation_resolution={"answer_obligation": "summarize_current_conversation"},
    )
    decision = merge_composer_into_retrieval_decision_v1(
        retrieval_decision={
            "retrieval_action": "concept_answer",
            "rag_included_count": 1,
            "rag_included_for_writer": [{"chunk_id": "c1", "content": "KB noise", "score": 0.9}],
        },
        composer_payload=composer,
    )

    assert decision["retrieval_action"] == "use_current_context_only"
    assert decision["rag_included_count"] == 0
    assert decision["rag_included_for_writer"] == []
    assert decision["composer"]["query_source"] == "summary_request"


def test_query_kb_composer_compacts_included_chunks() -> None:
    composer = build_contextual_retrieval_query_composer_v1(
        user_message="Что такое нейросталкинг?",
        dialogue_act_resolution={"dialogue_act": "knowledge_question"},
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )
    long_content = "нейросталкинг " * 200
    decision = merge_composer_into_retrieval_decision_v1(
        retrieval_decision={
            "retrieval_action": "concept_answer",
            "rag_included_count": 2,
            "rag_included_for_writer": [
                {"chunk_id": "c1", "content": long_content, "score": 0.9},
                {"chunk_id": "c2", "content": "second", "score": 0.8},
                {"chunk_id": "c3", "content": "third", "score": 0.7},
            ],
        },
        composer_payload=composer,
    )

    assert decision["retrieval_action"] == "query_kb"
    assert decision["rag_included_count"] <= composer["max_chunks_for_writer"]
    assert len(decision["rag_included_for_writer"][0]["content"]) <= composer["max_chars_per_chunk"]
    assert decision["writer_can_ignore_rag"] is False


def test_short_contextual_followup_composer_visible_in_decision() -> None:
    composer = build_contextual_retrieval_query_composer_v1(
        user_message="Да, хорошо",
        last_assistant_offer={
            "is_open": True,
            "offer_type": "explain_concept",
            "offer_text_summary": "Показать через нейросталкинг и автоматизм.",
        },
    )
    decision = merge_composer_into_retrieval_decision_v1(
        retrieval_decision={"rag_included_for_writer": [], "rag_included_count": 0},
        composer_payload=composer,
    )

    assert decision["contextual_retrieval_query_composer_version"] == "contextual_retrieval_query_composer_v1"
    assert decision["retrieval_query_source"] == "last_assistant_offer"
    assert decision["composed_retrieval_query"] != "Да, хорошо"
    assert "нейросталкинг" in decision["composed_retrieval_query"]
