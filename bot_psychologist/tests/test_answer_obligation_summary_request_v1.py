from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.answer_obligation_resolver import build_answer_obligation_resolver_v1
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1
from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1


def _summary_act() -> dict:
    return build_dialogue_act_resolution_v1(
        user_message="сделай резюме нашей беседы",
        dialogue_pragmatics={"is_contextual_followup": True},
        last_assistant_offer={"is_open": True, "offer_type": "practice"},
    )


def test_summary_request_sets_current_conversation_answer_obligation() -> None:
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=_summary_act(),
        last_assistant_offer={"is_open": True, "offer_type": "practice"},
        unanswered_question_state={},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )

    assert obligation["answer_obligation"] == "summarize_current_conversation"
    assert obligation["answer_required"] is True
    assert obligation["must_answer"] == "summary of current conversation"
    assert obligation["summary_scope"] == "current_conversation"
    assert obligation["should_not_confirm_last_offer"] is True
    assert obligation["no_practice_unless_requested"] is True


def test_final_answer_directive_exposes_summary_metadata() -> None:
    act = _summary_act()
    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={"is_open": True, "offer_type": "practice"},
        unanswered_question_state={"answer_required": False, "answer_status": "answered"},
        dialogue_style_state={},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    directive = build_final_answer_directive_v1(
        user_message="сделай резюме нашей беседы",
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "profile_preset": "free_dialogue_default",
            "dialogue_act_resolution": act,
            "last_assistant_offer": {
                "is_open": True,
                "offer_type": "practice",
                "offer_text_summary": "Могу дать практику наблюдения.",
            },
            "unanswered_question_state": {"answer_required": False, "answer_status": "answered"},
        },
        dialogue_pragmatics={"is_contextual_followup": True},
        response_planner={"answer_shape": "one_step", "practice_policy": "optional_if_relevant"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
        answer_obligation_resolution=obligation,
    ).to_dict()

    assert directive["dialogue_act"] == "summary_request"
    assert directive["answer_obligation"] == "summarize_current_conversation"
    assert directive["must_answer"] == "summary of current conversation"
    assert directive["answer_shape"] == "structured_summary"
    assert directive["question_policy"] == "none"
    assert directive["practice_policy"] == "forbidden"
    assert directive["summary_request"] is True
    assert directive["summary_scope"] == "current_conversation"
    assert directive["no_confirmation_needed"] is True
    assert directive["no_practice_unless_requested"] is True


def _gate(final_answer: str, *, anchors: list[str] | None = None) -> dict:
    return build_final_answer_acceptance_gate_v1(
        user_message="подведи итог нашего разговора",
        final_answer=final_answer,
        dialogue_act_resolution={"dialogue_act": "summary_request"},
        answer_obligation_resolution={"answer_obligation": "summarize_current_conversation"},
        unanswered_question_state_before={"answer_required": False, "answer_status": "answered"},
        last_assistant_offer_before={"is_open": True, "offer_type": "practice"},
        dialogue_style_state={},
        final_answer_directive={
            "summary_request": True,
            "summary_scope": "current_conversation",
            "must_answer": "summary of current conversation",
            "summary_context_anchors": anchors or [],
        },
        writer_debug={},
        validator_result=SimpleNamespace(is_blocked=False),
        previous_assistant_message="Могу дать один практический шаг, если хочешь.",
    )


def test_gate_blocks_summary_reconfirmation_instead_of_answer() -> None:
    payload = _gate("Хочешь, чтобы я подвел итог нашего разговора?")

    assert payload["status"] == "failed"
    assert "summary_request_reconfirmed_instead_of_answered" in payload["failed_checks"]
    assert payload["retry_recommended"] is True


def test_gate_blocks_answering_last_offer_instead_of_summary() -> None:
    payload = _gate("Да, могу так сделать после подтверждения: выбери формат практики.")

    assert payload["status"] == "failed"
    assert "summary_answered_last_offer_instead" in payload["failed_checks"]


def test_gate_accepts_real_summary_and_does_not_seed_last_offer() -> None:
    payload = _gate(
        (
            "Итог разговора такой: ты описывал напряжение перед действием, "
            "автоматический контроль и желание увидеть свои реакции до того, как они уводят ресурс. "
            "Мы вышли на фокус: отделять факт ситуации от внутреннего прогноза и замечать момент выбора."
        ),
        anchors=["напряжение перед действием", "автоматический контроль", "момент выбора"],
    )

    assert payload["status"] == "passed"
    assert payload["can_save_last_assistant_offer"] is False
    assert payload["quality_signals"]["summary_request"] is True
