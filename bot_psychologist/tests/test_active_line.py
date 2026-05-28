from __future__ import annotations

from bot_agent.multiagent.active_line import build_active_line_state, classify_user_intent


def test_intent_understand_mechanism() -> None:
    assert classify_user_intent("хочу разобраться, в чем механизм") == "understand_mechanism"


def test_intent_correction_of_bot() -> None:
    assert (
        classify_user_intent("почему ты мне предлагаешь практику? я ведь хочу разобраться")
        == "correction_of_bot"
    )


def test_intent_ask_for_direct_step() -> None:
    assert classify_user_intent("дай один конкретный шаг") == "ask_for_direct_step"


def test_intent_thanks_close() -> None:
    assert classify_user_intent("спасибо") == "thanks_close"


def test_forecasting_work_dialogue_builds_active_line() -> None:
    payload = build_active_line_state(
        user_message="На работе. Я слишком много думаю прежде чем действовать",
        conversation_context="",
        response_mode="reflect",
        practice_allowed=False,
    ).to_dict()
    assert "старт" in payload["active_line"] or "прогноз" in payload["active_line"]


def test_practice_forbidden_when_user_asks_understand() -> None:
    payload = build_active_line_state(
        user_message="Только не предлагай практику, помоги понять механизм",
        conversation_context="",
        response_mode="reflect",
        practice_allowed=True,
    ).to_dict()
    assert payload["should_offer_practice"] is False
    assert payload["practice_suppression_active"] is True


def test_repair_mode_disables_practice() -> None:
    payload = build_active_line_state(
        user_message="Почему ты мне предлагаешь практику?",
        conversation_context="предыдущая линия",
        response_mode="reflect",
        practice_allowed=True,
    ).to_dict()
    assert payload["repair_mode"]
    assert payload["should_offer_practice"] is False


def test_revoicing_disallowed_for_continuity_turn() -> None:
    payload = build_active_line_state(
        user_message="да, я откладываю старт, но когда начинаю, чувствую что уже устал",
        conversation_context="User: ...\nAssistant: ...",
        response_mode="reflect",
        practice_allowed=False,
    ).to_dict()
    assert payload["continuity_mode"] == "continue_existing_line"
    assert payload["revoicing_allowed"] is False
