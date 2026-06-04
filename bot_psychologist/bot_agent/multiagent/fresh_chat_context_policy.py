"""Fresh chat isolation policy for writer/runtime context shaping."""

from __future__ import annotations

import re
from typing import Any


FRESH_CHAT_CONTEXT_POLICY_VERSION = "fresh_chat_context_policy_v1"

_GREETING_MARKERS = (
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "hello",
    "hi",
    "hey",
)
_CONTACT_MARKERS = (
    "рад знакомству",
    "хочу познакомиться",
    "просто пишу впервые",
    "первый раз пишу",
    "давай познакомимся",
    "можем познакомиться",
)
_CONTINUATION_MARKERS = (
    "продолжим",
    "вернемся",
    "вернёмся",
    "как мы говорили",
    "как ты писал",
    "как ты говорила",
    "прошлый чат",
    "предыдущий чат",
    "continue",
    "as we discussed",
)
_QUESTION_MARKERS = (
    "?",
    "что такое",
    "как",
    "почему",
    "зачем",
    "какие",
    "объясни",
    "расскажи",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def is_explicit_continuation_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _CONTINUATION_MARKERS)


def is_greeting_or_contact_message(user_message: str) -> bool:
    lowered = _normalize(user_message)
    if not lowered:
        return False
    starts_with_greeting = any(lowered.startswith(marker) for marker in _GREETING_MARKERS)
    mentions_contact = any(marker in lowered for marker in _CONTACT_MARKERS)
    short_contact = starts_with_greeting and len(lowered) <= 120
    return bool(starts_with_greeting or mentions_contact or short_contact)


def has_explicit_question_or_knowledge_need(
    user_message: str,
    *,
    knowledge_answer_guard: dict[str, Any] | None = None,
) -> bool:
    lowered = _normalize(user_message)
    if any(marker in lowered for marker in _QUESTION_MARKERS):
        return True
    guard = dict(knowledge_answer_guard or {})
    knowledge_answer = (
        dict(guard.get("knowledge_answer", {}))
        if isinstance(guard.get("knowledge_answer"), dict)
        else {}
    )
    return bool(knowledge_answer.get("needed", False))


def build_fresh_chat_context_policy_v1(
    *,
    user_message: str,
    recent_turns: list[dict[str, Any]] | None,
    knowledge_answer_guard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    turns = [item for item in list(recent_turns or []) if isinstance(item, dict)]
    turn_index = max(1, len(turns) + 1)
    is_new_chat = len(turns) == 0
    in_fresh_window = turn_index <= 2
    continuation_requested = is_explicit_continuation_request(user_message)
    greeting_or_contact = is_greeting_or_contact_message(user_message)
    explicit_question = has_explicit_question_or_knowledge_need(
        user_message,
        knowledge_answer_guard=knowledge_answer_guard,
    )

    cross_session_memory_allowed = not (
        in_fresh_window and greeting_or_contact and not continuation_requested and not explicit_question
    )
    if cross_session_memory_allowed:
        if continuation_requested:
            reason = "explicit_continuation"
        elif explicit_question:
            reason = "explicit_question_or_knowledge_need"
        else:
            reason = "current_chat_runtime_scope"
    elif greeting_or_contact:
        reason = "fresh_greeting_no_explicit_continuation"
    elif is_new_chat:
        reason = "new_chat_first_turn_current_chat_only"
    else:
        reason = "fresh_window_current_chat_only"

    return {
        "version": FRESH_CHAT_CONTEXT_POLICY_VERSION,
        "is_new_chat": bool(is_new_chat),
        "turn_index": int(turn_index),
        "fresh_window_active": bool(in_fresh_window),
        "is_greeting_or_contact": bool(greeting_or_contact),
        "explicit_continuation_requested": bool(continuation_requested),
        "explicit_question_or_knowledge_need": bool(explicit_question),
        "cross_session_memory_allowed": bool(cross_session_memory_allowed),
        "cross_session_memory_reason": reason,
        "active_context_source": (
            "current_chat_only" if not cross_session_memory_allowed else "current_chat_runtime_scope"
        ),
    }


__all__ = [
    "FRESH_CHAT_CONTEXT_POLICY_VERSION",
    "build_fresh_chat_context_policy_v1",
    "has_explicit_question_or_knowledge_need",
    "is_explicit_continuation_request",
    "is_greeting_or_contact_message",
]
