from __future__ import annotations

from bot_agent.multiagent.dialogue_act_resolver import (
    build_dialogue_act_resolution_v1,
    detect_summary_request_route_v1,
)


def test_explicit_summary_request_outranks_open_last_offer_confirmation() -> None:
    payload = build_dialogue_act_resolution_v1(
        user_message="подведи итог нашего разговора",
        dialogue_pragmatics={"is_contextual_followup": True},
        last_assistant_offer={
            "is_open": True,
            "offer_type": "practice",
            "offer_text_summary": "Могу дать один практический шаг.",
        },
    )

    assert payload["dialogue_act"] == "summary_request"
    assert payload["summary_scope"] == "current_conversation"
    assert payload["should_not_confirm_last_offer"] is True
    assert payload["no_confirmation_needed"] is True


def test_summary_request_detects_recap_wording() -> None:
    payload = detect_summary_request_route_v1("собери всё вместе: к чему мы пришли?")

    assert payload["is_summary_request"] is True
    assert payload["summary_scope"] == "current_conversation"
    assert payload["reason"] == "explicit_current_conversation_summary_request"


def test_short_yes_still_answers_last_offer_when_not_summary() -> None:
    payload = build_dialogue_act_resolution_v1(
        user_message="да",
        dialogue_pragmatics={"is_contextual_followup": True},
        last_assistant_offer={"is_open": True, "offer_type": "example"},
    )

    assert payload["dialogue_act"] == "confirmation_to_last_offer"


def test_direct_next_step_question_is_not_summary_request() -> None:
    payload = build_dialogue_act_resolution_v1(
        user_message="в итоге что мне делать прямо сейчас?",
        last_assistant_offer={"is_open": True, "offer_type": "practice"},
    )

    assert payload["dialogue_act"] != "summary_request"


def test_external_document_summary_is_not_current_conversation_summary() -> None:
    payload = detect_summary_request_route_v1("подведи итог по документу, который я прислал")

    assert payload["is_summary_request"] is False
    assert payload["reason"] == "summary_negative_marker"
