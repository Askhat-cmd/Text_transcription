from __future__ import annotations

from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile


def _bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-1",
                "source": "internal_doc",
                "content": "Internal knowledge chunk about a concept.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )


def test_support_turn_hides_writer_visible_grounding_by_default(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message="Меня бесит начальник, я уже не понимаю, что со мной.",
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_suppressed_reason": "non_kb_emotional_support_turn",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about a concept.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    visibility = package["writer_grounding_visibility_v1"]

    assert visibility["kb_visible_to_writer"] is False
    assert visibility["semantic_cards_visible_to_writer"] is False
    assert visibility["reason"] == "non_kb_emotional_support_turn"
    assert package["rag_for_writer"] == []
    assert package["writer_kb_payload"]["chunk_count"] == 0
    assert package["writer_kb_payload_trace"]["fallback_reason"] == visibility["reason"]
    assert package["retrieval_context"]["chunks"] == []


def test_direct_kb_question_keeps_grounding_visible(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message='Что такое программа "Несовершенное Я"?',
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
            "rag_included_count": 1,
            "rag_included_reason": "selected_for_writer",
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about a concept.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    visibility = package["writer_grounding_visibility_v1"]

    assert visibility["kb_visible_to_writer"] is True
    assert visibility["semantic_cards_visible_to_writer"] is True
    assert visibility["direct_kb_question"] is True
    assert len(package["rag_for_writer"]) == 1
    assert package["writer_kb_payload"]["chunk_count"] >= 1


def test_semantic_cards_become_trace_only_on_simplify_turn(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    def _selected_cards(**_: object) -> dict:
        return {
            "schema_version": "semantic_cards_pilot_trace_v1",
            "status": "selected",
            "selected_card_count": 1,
            "selected_card_ids": ["program_imperfect_self_v1"],
            "writer_payload_enriched": True,
            "payload_items": [
                {
                    "chunk_id": "semantic_card:program_imperfect_self_v1",
                    "source": "semantic_cards_pilot_v1",
                    "content": "Card support text.",
                    "allowed_use": ["writer_support"],
                    "chunk_type": "concept",
                }
            ],
        }

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_cards)

    package = build_writer_context_package_v1(
        user_message="Ты слишком сложно сказал, скажи проще.",
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about a concept.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={"simplify": True},
    )

    semantic_trace = package["semantic_cards_pilot"]

    assert package["writer_grounding_visibility_v1"]["semantic_cards_visible_to_writer"] is False
    assert semantic_trace["status"] == "trace_only"
    assert semantic_trace["selected_card_count"] == 1
    assert semantic_trace["writer_payload_enriched"] is False
    assert package["semantic_card_payload_items"] == []


def test_explicit_practice_request_allows_only_narrow_grounding_types(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    import bot_agent.multiagent.writer_context_package as package_module

    def _selected_cards(**_: object) -> dict:
        return {
            "schema_version": "semantic_cards_pilot_trace_v1",
            "status": "selected",
            "selected_card_count": 2,
            "selected_card_ids": ["practice_card_v1", "theory_card_v1"],
            "writer_payload_enriched": True,
            "payload_items": [
                {
                    "chunk_id": "semantic_card:practice_card_v1",
                    "source": "semantic_cards_pilot_v1",
                    "content": "Pause before replying.",
                    "allowed_use": ["writer_support"],
                    "chunk_type": "practice",
                },
                {
                    "chunk_id": "semantic_card:theory_card_v1",
                    "source": "semantic_cards_pilot_v1",
                    "content": "Long theory about control.",
                    "allowed_use": ["writer_support"],
                    "chunk_type": "concept",
                },
            ],
        }

    monkeypatch.setattr(package_module, "build_semantic_cards_pilot_selection", _selected_cards)

    bundle = MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-practice",
                "source": "internal_doc",
                "content": "Name the trigger and pause before replying.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "practice"},
            },
            {
                "chunk_id": "kb-theory",
                "source": "internal_doc",
                "content": "Broad concept dump about control and self-worth.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "concept"},
            },
        ],
        has_relevant_knowledge=True,
        context_turns=3,
    )

    package = build_writer_context_package_v1(
        user_message="Дай мне какую-нибудь практику, чтобы не быть реактивным в разговоре с начальником.",
        memory_bundle=bundle,
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "practice_context",
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
                    "chunk_id": "kb-theory",
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

    visibility = package["writer_grounding_visibility_v1"]

    assert visibility["kb_visible_to_writer"] is True
    assert visibility["semantic_cards_visible_to_writer"] is True
    assert visibility["reason"] == "explicit_practice_request_narrow_grounding"
    assert visibility["allowed_grounding_types"] == ["practice"]
    assert {item["chunk_id"] for item in package["rag_for_writer"]} == {"kb-practice"}
    assert {item["chunk_id"] for item in package["semantic_card_payload_items"]} == {
        "semantic_card:practice_card_v1"
    }
    assert all(
        chunk["chunk_type"] == "practice"
        for chunk in package["writer_kb_payload"]["chunks"]
    )


def test_no_internal_db_still_suppresses_practice_grounding(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message="Дай мне практику, чтобы не срываться на начальника.",
        memory_bundle=MemoryBundle(
            conversation_context="",
            user_profile=UserProfile(),
            knowledge_rag_hits=[
                {
                    "chunk_id": "kb-practice",
                    "source": "internal_doc",
                    "content": "Pause before replying.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "practice"},
                }
            ],
            has_relevant_knowledge=True,
            context_turns=2,
        ),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "practice_context",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-practice",
                    "source": "internal_doc",
                    "content": "Pause before replying.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "practice"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={"no_internal_db": True},
    )

    visibility = package["writer_grounding_visibility_v1"]

    assert visibility["reason"] == "latest_turn_no_internal_db"
    assert visibility["kb_visible_to_writer"] is False
    assert visibility["semantic_cards_visible_to_writer"] is False
    assert package["rag_for_writer"] == []
    assert package["semantic_card_payload_items"] == []
    assert package["writer_kb_payload"]["chunk_count"] == 0


def test_knowledge_policy_still_blocks_internal_only_and_do_not_use() -> None:
    decisions, trace = apply_knowledge_policy_v1(
        [
            {
                "chunk_id": "internal-1",
                "source": "src",
                "score": 0.8,
                "content": "Internal only content.",
                "governance": {
                    "chunk_type": "concept",
                    "allowed_use": ["writer_context", "internal_only"],
                    "safety_flags": [],
                },
            },
            {
                "chunk_id": "drop-1",
                "source": "src",
                "score": 0.7,
                "content": "Do not use content.",
                "governance": {
                    "chunk_type": "excluded",
                    "allowed_use": ["do_not_use"],
                    "safety_flags": [],
                },
            },
        ]
    )

    assert [item.action for item in decisions] == ["internal_only", "drop"]
    assert [item.allowed_for_writer for item in decisions] == [False, False]
    assert trace["included_writer_count"] == 0
