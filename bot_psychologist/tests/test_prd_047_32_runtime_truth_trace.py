from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.writer_context_package import (
    build_writer_context_package_v1,
    build_writer_grounding_visibility_v1,
)


def _practice_bundle() -> MemoryBundle:
    practice = {
        "chunk_id": "kb-practice",
        "source": "internal_doc",
        "content": "Name the trigger and pause before replying.",
        "allowed_use": ["writer_support"],
        "chunking_quality": {"chunk_type": "practice"},
    }
    concept = {
        "chunk_id": "kb-concept",
        "source": "internal_doc",
        "content": "Broad concept dump about control and self-worth.",
        "allowed_use": ["writer_support"],
        "chunking_quality": {"chunk_type": "concept"},
    }
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        semantic_hits=[
            SemanticHit(
                chunk_id="trace-only-hit",
                source="memory",
                score=0.7,
                content="Trace-only memory hit.",
                chunking_quality={"chunk_type": "concept"},
            )
        ],
        knowledge_rag_hits=[practice, concept],
        has_relevant_knowledge=True,
        context_turns=3,
    )


def test_runtime_truth_separates_candidates_filtered_and_writer_payload(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    def _selected_cards(**_: object) -> dict:
        return {
            "schema_version": "semantic_cards_pilot_trace_v1",
            "status": "selected",
            "selected_card_count": 2,
            "selected_card_ids": ["practice-card", "concept-card"],
            "writer_payload_enriched": True,
            "payload_items": [
                {
                    "chunk_id": "semantic_card:practice-card",
                    "semantic_card_id": "practice-card",
                    "semantic_card_pack_id": "semantic_cards_pilot_v1",
                    "payload_item_origin": "semantic_card",
                    "source": "semantic_cards_pilot_v1",
                    "content": "Use one bounded noticing step.",
                    "allowed_use": ["writer_support"],
                    "chunk_type": "practice",
                },
                {
                    "chunk_id": "semantic_card:concept-card",
                    "semantic_card_id": "concept-card",
                    "semantic_card_pack_id": "semantic_cards_pilot_v1",
                    "payload_item_origin": "semantic_card",
                    "source": "semantic_cards_pilot_v1",
                    "content": "Long conceptual theory.",
                    "allowed_use": ["writer_support"],
                    "chunk_type": "concept",
                },
            ],
        }

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_cards)

    package = build_writer_context_package_v1(
        user_message="Дай мне какую-нибудь практику, чтобы не быть реактивным.",
        memory_bundle=_practice_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "practice_context",
            "retrieval_query_source": "current_turn_focus_v1",
            "rag_included_count": 2,
            "rag_included_reason": "selected_for_writer",
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-practice",
                    "source": "internal_doc",
                    "content": "Name the trigger and pause before replying.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "practice"},
                },
                {
                    "chunk_id": "kb-concept",
                    "source": "internal_doc",
                    "content": "Broad concept dump about control and self-worth.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                },
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    truth = package["runtime_truth_trace_v1"]
    payload_trace = package["writer_kb_payload_trace"]

    assert truth["trace_version"] == "runtime_truth_trace_v1"
    assert truth["writer_visible_payload_count"] == payload_trace["payload_chunk_count"]
    assert truth["writer_visible_payload_count"] == 2
    assert set(truth["writer_visible_payload_types"]) == {"practice"}
    assert truth["filtered_out_for_writer_count"] >= 2
    assert any(
        item["item_id"] == "kb-concept"
        and item["sent_to_writer"] is False
        and item["filter_reason"] == "filtered_by_narrow_practice_grounding"
        for item in truth["filtered_out_for_writer"]
    )
    assert any(
        item["item_id"] == "semantic_card:concept-card"
        and item["filter_reason"] == "filtered_by_narrow_practice_grounding"
        for item in truth["filtered_out_for_writer"]
    )
    assert all(item["sent_to_writer"] is True for item in truth["writer_visible_payload_items"])
    assert all(item["applied_as_authority"] is False for item in truth["writer_visible_payload_items"])


def test_runtime_truth_keeps_broad_kb_hidden_on_ordinary_support(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message="I just need support, no practice.",
        memory_bundle=_practice_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "retrieval_query_source": "current_turn_focus_v1",
            "rag_suppressed_reason": "ordinary_support_trace_only",
            "rag_included_count": 0,
            "rag_included_for_writer": [],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    truth = package["runtime_truth_trace_v1"]

    assert truth["writer_visible_payload_count"] == 0
    assert truth["broad_kb_visible"] is False
    assert truth["filtered_out_for_writer_count"] > 0
    assert all(item["sent_to_writer"] is False for item in truth["filtered_out_for_writer"])


def test_direct_internal_base_source_question_overrides_stale_followup() -> None:
    user_message = "Что во внутренней базе говорится про программу несовершенное Я?"

    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={"is_contextual_followup": True},
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )
    visibility = build_writer_grounding_visibility_v1(
        user_message=user_message,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
        },
        latest_turn_constraints={},
        has_grounding_candidates=True,
        candidate_chunk_types=["concept"],
    )

    assert act["dialogue_act"] == "knowledge_question"
    assert act["source"] == "explicit_direct_question_override"
    assert visibility["direct_source_request"] is True
    assert visibility["kb_visible_to_writer"] is True
    assert visibility["reason"] == "direct_source_request"
