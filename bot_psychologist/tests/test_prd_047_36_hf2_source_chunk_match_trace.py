from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _build_package(
    *,
    user_message: str,
    raw_hit_summaries: list[dict],
    rag_items: list[dict],
    semantic_hits: list[SemanticHit] | None = None,
    retrieval_decision: dict | None = None,
    knowledge_rag_hits: list[dict] | None = None,
) -> dict:
    resolved_retrieval_decision = retrieval_decision or {
        "retrieval_action": "query_kb",
        "retrieval_need": "knowledge_context",
        "retrieval_query_source": "current_turn_focus_v1",
        "rag_included_count": len(rag_items),
        "rag_included_reason": "selected_for_writer",
        "rag_included_for_writer": list(rag_items),
    }
    memory_bundle = MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        semantic_hits=list(semantic_hits or []),
        knowledge_rag_hits=list(knowledge_rag_hits if knowledge_rag_hits is not None else rag_items),
        has_relevant_knowledge=bool(rag_items),
        context_turns=1,
        rag_retrieval_trace={
            "version": "rag_retrieval_trace_v1",
            "query": user_message,
            "raw_hit_summaries": list(raw_hit_summaries),
        },
    )
    return build_writer_context_package_v1(
        user_message=user_message,
        memory_bundle=memory_bundle,
        context_package=None,
        retrieval_decision=resolved_retrieval_decision,
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )


def test_source_chunk_match_trace_marks_raw_source_loss_when_no_matching_raw_hit(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    rag_item = {
        "chunk_id": "kb-unrelated",
        "source": "internal_doc",
        "source_doc": "ГЛАВА 1",
        "content": "Программа несовершенное Я держится на автоматизме и самокритике.",
        "allowed_use": ["writer_context"],
        "chunking_quality": {"chunk_type": "concept"},
    }
    package = _build_package(
        user_message="Что такое анестетическая депрессия?",
        raw_hit_summaries=[
            {
                "chunk_id": "raw-1",
                "source_doc": "ГЛАВА 1",
                "score": 0.01,
                "rank": 1,
                "chunk_type": "general_text",
                "allowed_use": [],
                "quote_policy": "paraphrase_only",
                "preview": "Программа несовершенное Я держится на автоматизме и самокритике.",
            }
        ],
        rag_items=[rag_item],
        semantic_hits=[
            SemanticHit(
                chunk_id="raw-1",
                source="ГЛАВА 1",
                score=0.01,
                content="Программа несовершенное Я держится на автоматизме и самокритике.",
            )
        ],
    )

    trace = package["runtime_truth_trace_v1"]["source_chunk_match_trace_v1"]

    assert trace["enabled"] is True
    assert trace["explicit_knowledge_question"] is True
    assert "анестетическая" in trace["focus_terms"]
    assert trace["loss_stage"] == "raw_source"
    assert trace["loss_reason"] == "no_raw_source_match_in_runtime_top_k"
    assert trace["best_raw_match"]["near_exact_match"] is False


def test_source_chunk_match_trace_proves_exact_match_reaches_payload(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    rag_item = {
        "chunk_id": "kb-concept-1",
        "source": "internal_doc",
        "source_doc": "Нейросталкинг",
        "content": "Программа несовершенное Я - это внутренний автопилот, который удерживает стыд и самокритику.",
        "allowed_use": ["writer_context"],
        "chunking_quality": {"chunk_type": "general_text"},
    }
    package = _build_package(
        user_message="Что такое программа несовершенное Я?",
        raw_hit_summaries=[
            {
                "chunk_id": "kb-concept-1",
                "source_doc": "Нейросталкинг",
                "score": 0.82,
                "rank": 1,
                "chunk_type": "general_text",
                "allowed_use": ["writer_context"],
                "quote_policy": "paraphrase_only",
                "preview": "Программа несовершенное Я - это внутренний автопилот, который удерживает стыд и самокритику.",
            }
        ],
        rag_items=[rag_item],
        semantic_hits=[
            SemanticHit(
                chunk_id="kb-concept-1",
                source="Нейросталкинг",
                score=0.82,
                content="Программа несовершенное Я - это внутренний автопилот, который удерживает стыд и самокритику.",
            )
        ],
    )

    truth = package["runtime_truth_trace_v1"]
    trace = truth["source_chunk_match_trace_v1"]

    assert truth["writer_visible_payload_count"] == 1
    assert trace["loss_stage"] == "none"
    assert trace["best_raw_match"]["chunk_id"] == "kb-concept-1"
    assert trace["best_raw_match"]["near_exact_match"] is True
    assert trace["best_runtime_match"]["sent_to_writer"] is True
    assert trace["payload_match"]["payload_position"] == 1
    assert trace["payload_match"]["near_exact_match"] is True


def test_direct_knowledge_general_text_chunk_is_not_dropped_only_for_chunk_type(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    rag_item = {
        "chunk_id": "kb-coma",
        "source": "internal_doc",
        "source_doc": "КУЗНИЦА ДУХА",
        "content": "Духовная кома - это состояние внутреннего онемения, когда старые смыслы уже не работают.",
        "allowed_use": ["direct_to_writer"],
        "chunking_quality": {"chunk_type": "general_text"},
    }
    package = _build_package(
        user_message="Что такое духовная кома?",
        raw_hit_summaries=[
            {
                "chunk_id": "kb-coma",
                "source_doc": "КУЗНИЦА ДУХА",
                "score": 0.77,
                "rank": 1,
                "chunk_type": "general_text",
                "allowed_use": ["direct_to_writer"],
                "quote_policy": "paraphrase_only",
                "preview": "Духовная кома - это состояние внутреннего онемения, когда старые смыслы уже не работают.",
            }
        ],
        rag_items=[rag_item],
        semantic_hits=[
            SemanticHit(
                chunk_id="kb-coma",
                source="КУЗНИЦА ДУХА",
                score=0.77,
                content="Духовная кома - это состояние внутреннего онемения, когда старые смыслы уже не работают.",
            )
        ],
    )

    truth = package["runtime_truth_trace_v1"]
    trace = truth["source_chunk_match_trace_v1"]
    payload_items = truth["writer_visible_payload_items"]

    assert truth["writer_visible_payload_count"] == 1
    assert payload_items[0]["chunk_type"] == "general_text"
    assert trace["loss_stage"] == "none"
    assert trace["payload_match"]["chunk_id"] == "kb-coma"


def test_direct_knowledge_recovers_policy_allowed_hit_when_explicit_gate_is_empty(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    rag_item = {
        "chunk_id": "kb-recovered-1",
        "source": "internal_doc",
        "source_doc": "Нейросталкинг",
        "content": "Программа несовершенное Я - это автоматический внутренний сценарий, который удерживает самокритику и стыд как способ выживания.",
        "allowed_use": ["direct_to_writer"],
        "chunking_quality": {"chunk_type": "general_text"},
    }
    package = _build_package(
        user_message="Что такое программа несовершенное Я?",
        raw_hit_summaries=[
            {
                "chunk_id": "kb-recovered-1",
                "source_doc": "Нейросталкинг",
                "score": 0.81,
                "rank": 1,
                "chunk_type": "general_text",
                "allowed_use": ["direct_to_writer"],
                "quote_policy": "paraphrase_only",
                "preview": "Программа несовершенное Я - это автоматический внутренний сценарий, который удерживает самокритику и стыд как способ выживания.",
            }
        ],
        rag_items=[],
        knowledge_rag_hits=[rag_item],
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
            "retrieval_query_source": "current_turn_focus_v1",
            "rag_included_count": 0,
            "rag_included_reason": "",
            "rag_included_for_writer": [],
        },
        semantic_hits=[
            SemanticHit(
                chunk_id="kb-recovered-1",
                source="Нейросталкинг",
                score=0.81,
                content="Программа несовершенное Я - это автоматический внутренний сценарий, который удерживает самокритику и стыд как способ выживания.",
            )
        ],
    )

    truth = package["runtime_truth_trace_v1"]
    trace = truth["source_chunk_match_trace_v1"]
    visibility = package["writer_grounding_visibility_v1"]

    assert package["retrieval_gate_recovery_applied"] is True
    assert truth["retrieval_gate_recovery_applied"] is True
    assert visibility["retrieval_gate_recovery_applied"] is True
    assert visibility["retrieval_gate_recovery_source"] == "memory_bundle.knowledge_rag_hits"
    assert package["rag_for_writer"][0]["chunk_id"] == "kb-recovered-1"
    assert truth["writer_visible_payload_count"] == 1
    assert trace["loss_stage"] == "none"
    assert trace["payload_match"]["chunk_id"] == "kb-recovered-1"
