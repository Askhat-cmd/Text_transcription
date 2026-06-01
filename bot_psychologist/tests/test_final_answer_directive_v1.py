from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1


def _build(user_message: str, *, profile: str = "mvp_free_dialogue", pragmatics: dict | None = None) -> dict:
    return build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy={"profile": profile},
        dialogue_pragmatics=pragmatics or {},
        response_planner={"answer_shape": "compact_direct", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()


def test_final_answer_directive_accepts_previous_offer_yes_followup() -> None:
    payload = _build(
        "да",
        pragmatics={
            "is_contextual_followup": True,
            "should_not_ask_confirmation_again": True,
            "previous_assistant_offer_type": "example",
        },
    )
    assert payload["user_intent"] == "accepted_previous_offer"
    assert payload["answer_obligation"] == "fulfill_previous_offer"
    assert payload["question_policy"] == "do_not_ask"


def test_final_answer_directive_repair_after_non_answer() -> None:
    payload = _build("ты не ответил мне на вопрос")
    assert payload["user_intent"] == "repair_after_failed_answer"
    assert payload["answer_obligation"] == "answer_previous_question_directly"
    assert payload["style"] == "brief_apology_then_direct_answer"


def test_final_answer_directive_concept_comparison() -> None:
    payload = _build("чем отличается Нейросталкинг от Неосталкинга?")
    assert payload["user_intent"] == "concept_comparison"
    assert payload["answer_obligation"] == "compare_two_concepts_directly"
    assert payload["answer_shape"] == "definition_then_difference_then_example"


def test_final_answer_directive_close_ack() -> None:
    payload = _build("спасибо")
    assert payload["user_intent"] == "close_ack"
    assert payload["answer_obligation"] == "close_gently"
    assert payload["rag_policy"] == "none"

