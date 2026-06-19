from __future__ import annotations

from bot_agent.knowledge.semantic_card_payload_adapter import build_semantic_cards_pilot_selection
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _empty_bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        knowledge_rag_hits=[],
        has_relevant_knowledge=False,
        context_turns=1,
    )


def test_semantic_cards_trace_reports_disabled_reason(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "false")

    trace = build_semantic_cards_pilot_selection(
        user_message='Что такое программа "Несовершенное Я"?',
    )

    assert trace["enabled"] is False
    assert trace["status"] == "disabled"
    assert trace["suppressed_reason"] == "disabled_by_config"
    assert trace["authority"] == "advisory_only"
    assert trace["writer_can_ignore"] is True
    assert trace["applied_as_authority"] is False


def test_semantic_cards_trace_exposes_loaded_count_and_selected_ids(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message='Что такое программа "Несовершенное Я"?',
        memory_bundle=_empty_bundle(),
        context_package=None,
        retrieval_decision={"rag_included_count": 0, "rag_included_for_writer": []},
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
    )

    semantic_trace = package["semantic_cards_pilot"]
    writer_trace = package["writer_kb_payload_trace"]

    assert semantic_trace["enabled"] is True
    assert semantic_trace["pack_id"] == "semantic_cards_pilot_v1"
    assert semantic_trace["loaded_card_count"] >= 12
    assert semantic_trace["selected_card_count"] >= 1
    assert "program_imperfect_self_v1" in semantic_trace["selected_card_ids"]
    assert semantic_trace["writer_payload_enriched"] is True

    chunk_summaries = list(writer_trace["chunk_summaries"])
    assert chunk_summaries
    assert chunk_summaries[0]["payload_item_origin"] == "semantic_card"
    assert chunk_summaries[0]["semantic_card_pack_id"] == "semantic_cards_pilot_v1"
    assert chunk_summaries[0]["semantic_card_id"] == "program_imperfect_self_v1"
    assert chunk_summaries[0]["writer_can_ignore"] is True
    assert chunk_summaries[0]["applied_as_authority"] is False


def test_semantic_cards_trace_shows_suppression_reason_without_hiding_pack_status(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")

    trace = build_semantic_cards_pilot_selection(
        user_message="Я выжат и не хочу теорию. Просто ответь по-человечески.",
    )

    assert trace["enabled"] is True
    assert trace["loaded_card_count"] >= 12
    assert trace["selected_card_count"] == 0
    assert trace["status"] == "suppressed"
    assert trace["suppressed_reason"] == "user_requested_no_theory"
    assert trace["writer_payload_enriched"] is False
