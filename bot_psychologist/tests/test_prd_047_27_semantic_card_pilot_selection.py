from __future__ import annotations

from bot_agent.knowledge.semantic_card_payload_adapter import (
    build_semantic_cards_pilot_selection,
    get_semantic_cards_pilot_config,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def test_feature_flag_default_off(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("SEMANTIC_CARDS_PILOT_ENABLED", raising=False)

    cfg = get_semantic_cards_pilot_config()

    assert cfg.enabled is False
    assert cfg.enabled_requested is False


def test_known_concept_question_selects_relevant_cards(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")

    trace = build_semantic_cards_pilot_selection(
        user_message='Что такое программа "Несовершенное Я"?',
        retrieval_decision={"mechanism_hints": ["imperfect_self"]},
    )

    assert trace["enabled"] is True
    assert 1 <= trace["selected_card_count"] <= 3
    assert "program_imperfect_self_v1" in trace["selected_card_ids"]
    assert trace["applied_as_authority"] is False
    assert trace["writer_can_ignore"] is True


def test_greeting_and_no_theory_suppress_cards(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")

    greeting = build_semantic_cards_pilot_selection(user_message="Привет! Я Олег.")
    no_theory = build_semantic_cards_pilot_selection(
        user_message="Я выжат и не хочу теорию. Просто ответь по-человечески."
    )

    assert greeting["selected_card_count"] == 0
    assert greeting["suppressed_reason"] == "greeting_or_contact"
    assert no_theory["selected_card_count"] == 0
    assert no_theory["suppressed_reason"] == "user_requested_no_theory"


def test_practice_card_requires_explicit_practice_request(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")

    concept = build_semantic_cards_pilot_selection(user_message='Что такое драйвер "Будь сильным"?')
    practice = build_semantic_cards_pilot_selection(
        user_message='Дай одну короткую практику, чтобы заметить драйвер "Будь сильным".'
    )

    assert "one_bounded_practice_not_self_improvement_whip_v1" not in concept["selected_card_ids"]
    assert "one_bounded_practice_not_self_improvement_whip_v1" in practice["selected_card_ids"]


def test_writer_context_package_enriches_payload_without_replacing_rag(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    bundle = MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        knowledge_rag_hits=[],
        has_relevant_knowledge=False,
        context_turns=1,
    )

    package = build_writer_context_package_v1(
        user_message='Что такое программа "Несовершенное Я"?',
        memory_bundle=bundle,
        context_package=None,
        retrieval_decision={"rag_included_count": 0, "rag_included_for_writer": []},
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
    )

    trace = package["semantic_cards_pilot"]
    assert trace["selected_card_count"] >= 1
    assert package["rag_for_writer"] == []
    assert package["writer_kb_payload"]["chunk_count"] >= 1
    assert package["writer_kb_payload"]["chunks"][0]["chunk_id"].startswith("semantic_card:")
