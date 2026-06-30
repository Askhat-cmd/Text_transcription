from __future__ import annotations

import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1
from tools import prd_047_36_owner_pilot_readiness_gate_lib as gate


def _build_package(
    *,
    user_message: str,
    raw_hit_summaries: list[dict],
    rag_items: list[dict],
) -> dict:
    memory_bundle = MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        semantic_hits=[
            SemanticHit(
                chunk_id="trace-semantic-hit",
                source="runtime",
                score=0.62,
                content="runtime semantic hit",
            )
        ],
        knowledge_rag_hits=list(rag_items),
        has_relevant_knowledge=bool(rag_items),
        context_turns=1,
        rag_retrieval_trace={
            "version": "rag_retrieval_trace_v1",
            "query": user_message,
            "raw_hit_summaries": list(raw_hit_summaries),
        },
    )
    retrieval_decision = {
        "retrieval_action": "query_kb",
        "retrieval_need": "knowledge_context",
        "retrieval_query_source": "current_turn_focus_v1",
        "rag_included_count": len(rag_items),
        "rag_included_reason": "selected_for_writer",
        "rag_included_for_writer": list(rag_items),
    }
    return build_writer_context_package_v1(
        user_message=user_message,
        memory_bundle=memory_bundle,
        context_package=None,
        retrieval_decision=retrieval_decision,
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )


def test_trace_consistency_helper_flags_contradictory_fixture() -> None:
    payload = gate.build_trace_consistency_check(
        {
            "loss_stage": "raw_source",
            "loss_reason": "no_raw_source_match_in_runtime_top_k",
            "payload_match": {
                "near_exact_match": True,
                "sent_to_writer": True,
            },
            "best_runtime_match": {
                "near_exact_match": True,
            },
        }
    )
    assert payload["trace_consistency_v1"]["status"] == "warning"
    assert payload["trace_consistency_v1"]["warning"] == "payload_visible_but_loss_stage_raw_source"


def test_writer_context_package_marks_recovered_without_raw_source_match(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    package = _build_package(
        user_message="Что такое анестетическая депрессия?",
        raw_hit_summaries=[
            {
                "chunk_id": "raw-unrelated",
                "source_doc": "НейроСталкинг",
                "score": 0.05,
                "rank": 1,
                "chunk_type": "general_text",
                "allowed_use": ["writer_context"],
                "quote_policy": "paraphrase_only",
                "preview": "Программа несовершенное Я удерживает самокритику и стыд.",
            }
        ],
        rag_items=[
            {
                "chunk_id": "kb-aesthetic-1",
                "source": "internal_doc",
                "source_doc": "НейроСталкинг",
                "content": "Анестетическая депрессия — это состояние эмоционального онемения и внутренней пустоты.",
                "allowed_use": ["writer_context"],
                "chunking_quality": {"chunk_type": "general_text"},
            }
        ],
    )
    trace = package["runtime_truth_trace_v1"]["source_chunk_match_trace_v1"]
    assert trace["best_runtime_match"]["near_exact_match"] is True
    assert trace["payload_match"]["near_exact_match"] is True
    assert trace["loss_stage"] == "recovered_without_raw_source_match"
    assert trace["loss_reason"] == "payload_recovered_from_runtime_candidate_without_raw_source_top_k_match"
