from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        semantic_hits=[
            SemanticHit(
                chunk_id="kb-program-1",
                source="Нейросталкинг",
                score=0.86,
                content="Программа несовершенное Я удерживает стыд, самокритику и отказ от проб.",
                chunking_quality={"chunk_type": "concept"},
            )
        ],
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-program-1",
                "source": "internal_doc",
                "source_doc": "Нейросталкинг",
                "content": "Программа несовершенное Я удерживает стыд, самокритику и отказ от проб.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )


def _selected_semantic_card(**_: object) -> dict:
    return {
        "schema_version": "semantic_cards_pilot_trace_v1",
        "enabled": True,
        "status": "selected",
        "selected_card_count": 1,
        "selected_card_ids": ["program_imperfect_self_v1"],
        "writer_payload_enriched": True,
        "writer_can_ignore": True,
        "applied_as_authority": False,
        "payload_items": [
            {
                "chunk_id": "semantic_card:program_imperfect_self_v1",
                "semantic_card_id": "program_imperfect_self_v1",
                "semantic_card_pack_id": "semantic_cards_pilot_v1",
                "payload_item_origin": "semantic_card",
                "source": "semantic_cards_pilot_v1",
                "source_doc": "semantic_cards_pilot_v1",
                "content": "Программа несовершенное Я защищает от стыда ценой сужения выбора.",
                "core_thesis": "Программа несовершенное Я защищает от стыда ценой сужения выбора.",
                "allowed_use": ["writer_support"],
                "quote_policy": "paraphrase_only",
                "writer_instruction": "Use as hidden grounding.",
                "chunk_type": "concept",
                "writer_can_ignore": True,
                "applied_as_authority": False,
            }
        ],
    }


def test_direct_concept_followup_makes_selected_knowledge_writer_visible(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_semantic_card)

    package = build_writer_context_package_v1(
        user_message='Хочу понять, как "программа несовершенное Я" влияет на это.',
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_included_count": 0,
            "rag_included_for_writer": [],
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
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    visibility = package["writer_grounding_visibility_v1"]
    truth = package["runtime_truth_trace_v1"]

    assert visibility["reason"] == "direct_concept_followup"
    assert visibility["selected_knowledge_should_flow"] is True
    assert (
        visibility.get("selected_knowledge_recovery_applied") is True
        or visibility.get("retrieval_gate_recovery_applied") is True
    )
    assert package["writer_kb_payload"]["chunk_count"] >= 1
    assert truth["writer_visible_payload_count"] >= 1
    assert truth["grounding_visibility_reason"] == "direct_concept_followup"
    assert "semantic_card:program_imperfect_self_v1" in truth["writer_visible_payload_ids"]
    assert package["semantic_cards_pilot"]["status"] == "selected"


def test_no_internal_db_still_blocks_selected_followup_knowledge(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_semantic_card)

    package = build_writer_context_package_v1(
        user_message='Ответь без внутренней БД: как "программа несовершенное Я" влияет на это?',
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_included_count": 0,
            "rag_included_for_writer": [],
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
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={"no_internal_db": True},
    )

    visibility = package["writer_grounding_visibility_v1"]
    truth = package["runtime_truth_trace_v1"]

    assert visibility["reason"] == "latest_turn_no_internal_db"
    assert package["writer_kb_payload"]["chunk_count"] == 0
    assert truth["writer_visible_payload_count"] == 0
    assert package["semantic_cards_pilot"]["status"] == "suppressed"
