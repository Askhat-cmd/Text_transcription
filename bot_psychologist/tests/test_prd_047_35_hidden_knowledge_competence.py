from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        semantic_hits=[
            SemanticHit(
                chunk_id="trace-hit",
                source="memory",
                score=0.8,
                content="Trace-only semantic hit.",
                chunking_quality={"chunk_type": "concept"},
            )
        ],
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-concept",
                "source": "internal_doc",
                "content": "A hidden grounding note about panic and control.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )


def test_hidden_knowledge_competence_marks_public_user_mode_without_db_language() -> None:
    package = build_writer_context_package_v1(
        user_message="Я боюсь, что если меня сократят, я никому не буду нужен. Как распутать этот страх?",
        memory_bundle=_bundle(),
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

    hidden = package["hidden_knowledge_competence_v1"]
    truth = package["runtime_truth_trace_v1"]

    assert hidden["version"] == "hidden_knowledge_competence_v1"
    assert hidden["public_user_mode"] is True
    assert hidden["owner_debug_question_detected"] is False
    assert hidden["user_facing_db_language_suppressed"] is True
    assert hidden["knowledge_used_as_hidden_lens"] is True
    assert hidden["raw_kb_dump_allowed"] is False
    assert hidden["reason"] == "latest_turn"
    assert truth["hidden_knowledge_competence_v1"]["reason"] == "latest_turn"


def test_hidden_knowledge_competence_marks_owner_like_db_question_as_debug_trace_only() -> None:
    package = build_writer_context_package_v1(
        user_message="А что у тебя в базе говорится про панические атаки?",
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "retrieval_action": "query_kb",
            "retrieval_need": "knowledge_context",
            "retrieval_query_source": "current_turn_focus_v1",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-concept",
                    "source": "internal_doc",
                    "content": "A hidden grounding note about panic and control.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={},
    )

    hidden = package["hidden_knowledge_competence_v1"]
    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive={"latest_turn_constraints_v1": {"version": "latest_turn_constraints_v1", "active_constraints": []}},
        writer_debug=package,
        overlay_shadow={},
    )

    assert hidden["owner_debug_question_detected"] is True
    assert hidden["public_user_mode"] is True
    assert hidden["raw_kb_dump_allowed"] is False
    assert hidden["reason"] == "direct_source_debug"
    assert summary["hidden_knowledge_competence_v1"]["reason"] == "direct_source_debug"
