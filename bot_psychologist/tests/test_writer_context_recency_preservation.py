from __future__ import annotations

from bot_agent.multiagent.dialogue_policy import (
    format_conversation_context_for_writer,
    format_conversation_context_for_writer_with_meta,
)


def test_context_formatter_preserves_recent_turns_in_safe_guided() -> None:
    context = (
        ("OLD " * 1200)
        + "\nRECENT FULL TURNS:\n"
        + "USER#turn_8: блин! а что делать то\n"
        + "ASSISTANT#turn_8: сначала разберем механизм\n"
        + "USER#turn_9: не понял, подробнее\n"
        + "ASSISTANT#turn_9: давай разверну объяснение\n"
        + "USER#turn_10: скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть\n"
    )
    formatted, meta = format_conversation_context_for_writer_with_meta(
        conversation_context=context,
        profile="safe_guided",
        budget_chars=2800,
    )
    assert meta["context_truncated"] is True
    assert "older context omitted" in formatted
    assert "USER#turn_10: скажи, а в нейросталкинге" in formatted
    assert "USER#turn_9: не понял, подробнее" in formatted


def test_mvp_budget_keeps_more_context() -> None:
    context = ("A" * 3500) + "\nRECENT FULL TURNS:\nUSER#turn_1: x\nASSISTANT#turn_1: y"
    formatted = format_conversation_context_for_writer(
        context,
        "mvp_free_dialogue",
        7000,
    )
    assert "older context omitted" not in formatted
    assert "RECENT FULL TURNS" in formatted
