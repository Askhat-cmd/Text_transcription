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
                source="internal_doc",
                score=0.91,
                content="A concept chunk about self-criticism.",
                chunking_quality={"chunk_type": "concept"},
            )
        ],
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-program-1",
                "source": "internal_doc",
                "source_doc": "internal_doc",
                "content": "A concept chunk about self-criticism.",
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
        "payload_items": [
            {
                "chunk_id": "semantic_card:program_imperfect_self_v1",
                "semantic_card_id": "program_imperfect_self_v1",
                "source": "semantic_cards_pilot_v1",
                "source_doc": "semantic_cards_pilot_v1",
                "content": "Hidden concept support.",
                "allowed_use": ["writer_support"],
                "chunk_type": "concept",
            }
        ],
    }


def test_no_internal_db_boundary_trace_shows_explicit_payload_suppression(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_semantic_card)

    package = build_writer_context_package_v1(
        user_message="Answer without internal DB and without Neurostalking: what is self-realization?",
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-program-1",
                    "source": "internal_doc",
                    "source_doc": "internal_doc",
                    "content": "A concept chunk about self-criticism.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={
            "no_internal_db": True,
            "active_constraints": ["no_internal_db"],
            "source": "latest_user_turn_explicit_text",
        },
    )

    boundary = package["boundary_trace_v1"]
    truth_boundary = package["runtime_truth_trace_v1"]["boundary_trace_v1"]

    assert package["writer_grounding_visibility_v1"]["reason"] == "latest_turn_no_internal_db"
    assert package["writer_kb_payload"]["chunk_count"] == 0
    assert package["semantic_cards_pilot"]["status"] == "suppressed"
    assert truth_boundary == boundary
    assert boundary["boundary_flags"] == ["no_internal_db"]
    assert boundary["latest_turn_constraints"]["no_internal_db"] is True
    assert boundary["applied_suppressions"]["writer_kb_payload_suppressed"] is True
    assert boundary["applied_suppressions"]["semantic_cards_writer_visible_suppressed"] is True
    assert boundary["writer_payload_count"] == 0
    assert boundary["grounding_reason"] == "latest_turn_no_internal_db"
