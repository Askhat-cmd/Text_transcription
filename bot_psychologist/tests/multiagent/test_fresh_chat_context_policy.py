from __future__ import annotations

from bot_agent.multiagent.fresh_chat_context_policy import (
    build_fresh_chat_context_policy_v1,
)


def test_fresh_greeting_blocks_cross_session_memory() -> None:
    payload = build_fresh_chat_context_policy_v1(
        user_message="привет, меня зовут Асхат!",
        recent_turns=[],
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )

    assert payload["version"] == "fresh_chat_context_policy_v1"
    assert payload["is_new_chat"] is True
    assert payload["turn_index"] == 1
    assert payload["is_greeting_or_contact"] is True
    assert payload["cross_session_memory_allowed"] is False
    assert payload["cross_session_memory_reason"] == "fresh_greeting_no_explicit_continuation"
    assert payload["active_context_source"] == "current_chat_only"


def test_explicit_continuation_allows_cross_session_memory() -> None:
    payload = build_fresh_chat_context_policy_v1(
        user_message="продолжим прошлую тему про автоматический контроль",
        recent_turns=[],
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )

    assert payload["explicit_continuation_requested"] is True
    assert payload["cross_session_memory_allowed"] is True
    assert payload["cross_session_memory_reason"] == "explicit_continuation"
