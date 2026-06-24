from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from bot_agent.multiagent.agents.thread_manager import ThreadManagerAgent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1
from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.unanswered_question_tracker import build_unanswered_question_state_v1


def _snapshot() -> StateSnapshot:
    return StateSnapshot(
        nervous_state="window",
        intent="explore",
        openness="open",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.9,
    )


def test_generic_explicit_practice_request_without_question_mark_routes_to_practice_request() -> None:
    act = build_dialogue_act_resolution_v1(
        user_message="Дай мне какую нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным.",
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )

    assert act["dialogue_act"] == "practice_request"
    assert act["reason"] == "explicit_practice_request_without_question"
    assert act["source"] == "practice_request_override"


def test_practice_request_replaces_stale_unanswered_question_with_current_turn() -> None:
    payload = build_unanswered_question_state_v1(
        previous_state={
            "version": "unanswered_question_tracker_v1",
            "last_direct_user_question": "А если на меня накатывает гнев, а это мой начальник?",
            "turn_index": 3,
            "answer_required": True,
            "answer_status": "pending",
            "reason": "concrete_situation_question",
        },
        user_message="Дай мне какую нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным.",
        dialogue_act_resolution={"dialogue_act": "practice_request"},
        turn_index=4,
    )

    assert payload["last_direct_user_question"].startswith("Дай мне какую нибудь практику")
    assert payload["turn_index"] == 4
    assert payload["answer_required"] is True
    assert payload["reason"] == "practice_request"


def test_final_directive_uses_current_practice_request_as_must_answer() -> None:
    user_message = "Дай мне какую нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным."
    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": {"dialogue_act": "practice_request"},
            "unanswered_question_state": {
                "last_direct_user_question": "А если на меня накатывает гнев, а это мой начальник?",
                "answer_required": True,
                "answer_status": "pending",
            },
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "one_step", "question_policy": "none", "practice_policy": "allowed_if_explicit"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"retrieval_action": "trace_only"},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
        answer_obligation_resolution={
            "dialogue_act": "practice_request",
            "answer_obligation": "provide_one_bounded_practice",
            "answer_shape": "one_short_practice",
            "question_policy": "none",
            "practice_policy": "allowed_explicit_request",
            "depth": "short",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["answer_obligation"] == "provide_one_bounded_practice"
    assert directive["must_answer"] == user_message
    assert directive["question_policy"] == "none"


def test_acceptance_gate_rejects_generic_productivity_practice_for_explicit_request() -> None:
    user_message = "Дай мне какую-нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным."
    payload = build_final_answer_acceptance_gate_v1(
        user_message=user_message,
        final_answer="Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут.",
        dialogue_act_resolution={"dialogue_act": "practice_request"},
        answer_obligation_resolution={"answer_obligation": "provide_one_bounded_practice"},
        unanswered_question_state_before={
            "answer_required": True,
            "last_direct_user_question": user_message,
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": user_message},
        writer_debug={},
        validator_result=SimpleNamespace(is_blocked=False),
    )

    assert payload["status"] == "failed"
    assert "answer_does_not_address_direct_question" in payload["failed_checks"]


@pytest.mark.asyncio
async def test_explicit_practice_followup_keeps_current_thread_even_with_low_overlap() -> None:
    manager = ThreadManagerAgent()
    current = ThreadState(
        thread_id="chat2-thread",
        user_id="u-chat2",
        core_direction="меня злит что начальник врет в разговоре и я становлюсь реактивным",
        pattern_core="anger under boss-lie pressure",
        active_frame={
            "current_need": "gentle clarification",
            "next_recommended_direction": "reflect one key point and ask at most one question",
        },
        phase="clarify",
        turns_in_phase=3,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    updated = await manager.update(
        user_message="Дай мне какую нибудь практику. Чтобы я мог выработать в себе навык не быть реактивным.",
        state_snapshot=_snapshot(),
        user_id="u-chat2",
        current_thread=current,
        archived_threads=[],
    )

    assert updated.thread_id == "chat2-thread"
    assert updated.relation_to_thread == "continue"
    assert manager.last_debug["relation"]["relation_reason"] == "explicit_practice_request_continuation"
