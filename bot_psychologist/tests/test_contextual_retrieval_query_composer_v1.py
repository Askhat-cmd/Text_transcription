from __future__ import annotations

from bot_agent.multiagent.contextual_retrieval_query_composer import (
    build_contextual_retrieval_query_composer_v1,
)


def test_knowledge_question_composes_kb_query() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Что такое нейросталкинг?",
        dialogue_act_resolution={"dialogue_act": "knowledge_question"},
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )

    assert payload["version"] == "contextual_retrieval_query_composer_v1"
    assert payload["retrieval_action"] == "query_kb"
    assert payload["retrieval_need"] == "knowledge_context"
    assert "нейросталкинг" in payload["composed_query"]
    assert payload["include_for_writer_if_found"] is True
    assert payload["writer_can_ignore_rag"] is False
    assert payload["no_user_facing_text_created"] is True


def test_short_acceptance_of_concept_offer_uses_last_offer_query_not_literal_yes() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Да, хорошо",
        last_assistant_offer={
            "is_open": True,
            "offer_type": "explain_concept",
            "offer_text_summary": "Показать через нейросталкинг: автоматизм, защита и внутренний шаг.",
        },
        dialogue_pragmatics={
            "is_contextual_followup": True,
            "previous_assistant_offer_type": "explain_concept",
        },
    )

    assert payload["query_source"] == "last_assistant_offer"
    assert payload["retrieval_action"] == "query_kb"
    assert payload["composed_query"] != "Да, хорошо"
    assert "нейросталкинг" in payload["composed_query"]


def test_short_acceptance_of_short_support_suppresses_rag() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Да",
        last_assistant_offer={
            "is_open": True,
            "offer_type": "short_support",
            "offer_text_summary": "Хочешь, я просто поддержу тебя коротко, без разбора?",
        },
    )

    assert payload["retrieval_action"] == "suppress_rag"
    assert payload["retrieval_need"] == "none"
    assert payload["include_for_writer_if_found"] is False


def test_summary_request_uses_current_context_only() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Подведи краткий итог нашей беседы.",
        dialogue_act_resolution={"dialogue_act": "summary_request"},
        answer_obligation_resolution={"answer_obligation": "summarize_current_conversation"},
    )

    assert payload["retrieval_need"] == "conversation_context"
    assert payload["retrieval_action"] == "use_current_context_only"
    assert payload["query_source"] == "summary_request"
    assert payload["composed_query"] == ""
    assert payload["include_for_writer_if_found"] is False


def test_greeting_suppresses_rag() -> None:
    payload = build_contextual_retrieval_query_composer_v1(user_message="Привет")

    assert payload["retrieval_action"] == "suppress_rag"
    assert payload["suppress_reason"] == "contact_or_close_turn_no_kb_needed"


def test_practice_overview_queries_kb() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Какие практики есть?",
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "answer_type": "practice_overview"}},
    )

    assert payload["retrieval_need"] == "practice_context"
    assert payload["retrieval_action"] == "query_kb"
    assert "практики" in payload["composed_query"]


def test_one_step_request_suppresses_rag_without_knowledge_need() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Что сделать прямо сейчас?",
        response_planner={"answer_shape": "one_step"},
    )

    assert payload["retrieval_action"] == "suppress_rag"
    assert payload["include_for_writer_if_found"] is False


def test_external_document_summary_does_not_query_project_kb_by_default() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Подведи краткий итог документа",
        dialogue_act_resolution={"dialogue_act": "summary_request"},
        answer_obligation_resolution={"answer_obligation": "summarize_current_conversation"},
    )

    assert payload["retrieval_action"] == "use_current_context_only"
    assert payload["include_for_writer_if_found"] is False


def test_low_confidence_inherited_topic_is_trace_only() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Да",
        last_assistant_offer={"is_open": True, "offer_type": "unknown", "offer_text_summary": "Могу продолжить."},
    )

    assert payload["retrieval_action"] == "trace_only"
    assert payload["include_for_writer_if_found"] is False
