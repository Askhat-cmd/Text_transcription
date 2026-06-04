from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1


def test_greeting_final_answer_directive_uses_simple_contact() -> None:
    payload = build_final_answer_directive_v1(
        user_message="привет, меня зовут Асхат!",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "fresh_chat_context_policy": {
                "is_greeting_or_contact": True,
                "turn_index": 1,
                "cross_session_memory_allowed": False,
            },
            "explicit_answer_need": False,
        },
        dialogue_pragmatics={},
        response_planner={"answer_shape": "mechanism_explanation", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"rag_included_count": 0},
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()

    assert payload["answer_obligation"] == "respond_to_contact"
    assert payload["must_answer"] == "simple_contact"
    assert payload["answer_shape"] == "simple_contact"


def test_greeting_repair_final_answer_directive_uses_repair_shape() -> None:
    directive = build_final_answer_directive_v1(
        user_message="почему ты начал объяснять механизм, я просто поздоровался?",
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={"repair_user_dissatisfaction": True},
        response_planner={"answer_shape": "mechanism_explanation", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    )

    payload = directive.to_dict()
    assert payload["user_intent"] == "repair_after_failed_answer"
    assert payload["answer_obligation"] == "answer_previous_question_directly"
    assert payload["answer_shape"] == "repair_acknowledgement"
    assert payload["depth"] == "short"
    assert payload["question_policy"] == "do_not_ask_until_answered"
    assert payload["depth"] == "short"
