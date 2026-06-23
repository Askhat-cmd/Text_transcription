from __future__ import annotations

import json
from datetime import datetime, timezone

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.writer_context_package import build_writer_context_package_v1


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="prd-047-29-thread",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="",
        user_profile=UserProfile(),
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-1",
                "source": "internal_doc",
                "content": "Internal knowledge chunk about the concept.",
                "allowed_use": ["writer_support"],
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )


def test_writer_context_package_suppresses_writer_visible_payload_on_no_internal_db(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    package = build_writer_context_package_v1(
        user_message='Что такое программа "Несовершенное Я"?',
        memory_bundle=_bundle(),
        context_package=None,
        retrieval_decision={
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about the concept.",
                    "allowed_use": ["writer_support"],
                }
            ],
        },
        fresh_chat_context_policy={"cross_session_memory_allowed": True},
        latest_turn_constraints={"no_internal_db": True},
    )

    assert package["rag_for_writer"] == []
    assert package["semantic_card_payload_items"] == []
    assert package["semantic_cards_pilot"]["selected_card_count"] == 0
    assert package["semantic_cards_pilot"]["suppressed_reason"] == "latest_turn_no_internal_db"
    assert package["writer_kb_payload"]["chunk_count"] == 0
    assert package["writer_kb_payload_trace"]["fallback_reason"] == "latest_turn_no_internal_db"
    assert package["retrieval_context"]["chunks"] == []


def test_writer_contract_prompt_context_exposes_latest_turn_constraints_to_writer(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    contract = WriterContract(
        user_message="Не давай практику и отвечай без внутренней БД.",
        thread_state=_thread(),
        memory_bundle=_bundle(),
        retrieval_decision={
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about the concept.",
                    "allowed_use": ["writer_support"],
                }
            ],
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "answer_obligation": "answer_direct_question",
            "must_answer": "Не давай практику и отвечай без внутренней БД.",
            "answer_shape": "direct_answer",
            "depth": "short",
            "style": "simple, brief",
            "question_policy": "optional_none",
            "practice_policy": "forbidden_explicit_latest_turn",
            "diagnostic_center_role": "advisory_context_only",
            "planner_role": "advisory_context_only",
            "active_line_role": "advisory_context_only",
            "diagnostic_card_role": "advisory_context_only",
            "writer_autonomy": "medium",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_practice": True,
                "no_breathing_only": False,
                "simplify": False,
                "long_term_perspective": False,
                "no_internal_db": True,
                "active_constraints": ["no_practice", "no_internal_db"],
                "source": "latest_user_turn_explicit_text",
            },
        },
    )

    ctx = contract.to_prompt_context()
    directive = json.loads(ctx["writer_visible_final_answer_directive_json"])

    assert ctx["writer_visible_practice_instruction"] == "no_exercise_but_answer_normally"
    assert ctx["writer_context_package"]["rag_for_writer"] == []
    assert directive["latest_turn_constraints"]["no_practice"] is True
    assert directive["latest_turn_constraints"]["no_internal_db"] is True
