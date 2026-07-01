from __future__ import annotations

from bot_agent.multiagent.contextual_retrieval_query_composer import (
    build_contextual_retrieval_query_composer_v1,
)
from bot_agent.multiagent.writer_context_package import (
    build_writer_grounding_visibility_v1,
)


def test_greeting_still_suppresses_retrieval() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="привет!",
        memory_bundle_summary={
            "semantic_hits_count": 2,
            "has_relevant_knowledge": True,
            "fresh_chat_is_greeting_or_contact": True,
        },
    )

    assert payload["retrieval_action"] == "suppress_rag"
    assert payload["retrieval_need"] == "none"
    assert payload["suppress_reason"] == "contact_or_close_turn_no_kb_needed"


def test_concept_followup_composer_promotes_selected_knowledge() -> None:
    payload = build_contextual_retrieval_query_composer_v1(
        user_message="Хочу понять, как это влияет на самореализацию.",
        last_assistant_offer={
            "offer_type": "explanation",
            "offer_text_summary": "Кратко объяснил, что самореализация связана с внутренними защитами.",
        },
        dialogue_pragmatics={
            "is_contextual_followup": True,
            "inherited_topic": "самореализация",
        },
        memory_bundle_summary={
            "semantic_hits_count": 2,
            "has_relevant_knowledge": True,
        },
        current_concept="самореализация",
    )

    assert payload["retrieval_action"] == "query_kb"
    assert payload["retrieval_need"] == "knowledge_context"
    assert payload["include_for_writer_if_found"] is True
    assert payload["reason"] == "direct_concept_followup_selected_knowledge"
    assert "concept_followup" in payload["evidence"]
    assert payload["inherited_topic"] == "самореализация"


def test_writer_visibility_allows_direct_concept_followup_even_after_trace_only_gate() -> None:
    visibility = build_writer_grounding_visibility_v1(
        user_message='Хочу понять, как "программа несовершенное Я" влияет на это.',
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_suppressed_reason": "no_clear_retrieval_need",
            "contextual_retrieval_query_composer": {
                "reason": "direct_concept_followup_selected_knowledge",
                "inherited_topic": "самореализация",
                "evidence": [
                    "contextual_followup",
                    "selected_knowledge_available",
                    "concept_followup",
                ],
            },
        },
        latest_turn_constraints={},
        has_grounding_candidates=True,
        candidate_chunk_types=["concept"],
        selected_semantic_card_count=1,
    )

    assert visibility["kb_visible_to_writer"] is True
    assert visibility["semantic_cards_visible_to_writer"] is True
    assert visibility["reason"] == "direct_concept_followup"
    assert visibility["selected_knowledge_should_flow"] is True
    assert visibility["selected_semantic_card_count"] == 1
    assert visibility["writer_may_ignore_grounding"] is True
