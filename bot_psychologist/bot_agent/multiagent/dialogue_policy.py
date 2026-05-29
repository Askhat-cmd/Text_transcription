"""Unified dialogue policy profile helpers for multiagent runtime."""

from __future__ import annotations

import re
from typing import Any


DIALOGUE_PROFILE_SAFE_GUIDED = "safe_guided"
DIALOGUE_PROFILE_MVP_FREE = "mvp_free_dialogue"
ALLOWED_DIALOGUE_PROFILES = (
    DIALOGUE_PROFILE_SAFE_GUIDED,
    DIALOGUE_PROFILE_MVP_FREE,
)

_EXPANSION_MARKERS = (
    "развернуто",
    "развернут",
    "подробно",
    "подробнее",
    "полное объяснение",
    "полное разъяснение",
    "объясни нормально",
    "объясни подробнее",
    "я не понял",
    "не понимаю",
    "дай полный ответ",
    "максимально подробно",
)

_REPAIR_AND_EXPAND_MARKERS = (
    "я не понял",
    "не понимаю",
    "это не ответ",
    "объясни нормально",
    "дай понятный полный ответ",
)

_SHORT_SUPPORT_MARKERS = (
    "коротко",
    "без анализа",
    "просто поддержи",
    "мне плохо",
    "не вывожу",
    "не справляюсь",
)


def normalize_dialogue_profile(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in ALLOWED_DIALOGUE_PROFILES:
        return candidate
    return DIALOGUE_PROFILE_SAFE_GUIDED


def detect_expansion_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _EXPANSION_MARKERS)


def detect_repair_and_expand_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _REPAIR_AND_EXPAND_MARKERS)


def detect_short_support_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _SHORT_SUPPORT_MARKERS)


def extract_last_active_concept(active_frame: dict[str, Any] | None) -> str:
    if not isinstance(active_frame, dict):
        return ""
    return str(active_frame.get("active_concept", "") or "").strip().lower()


def apply_active_concept_continuation(
    *,
    user_message: str,
    dialogue_profile: str,
    knowledge_answer_guard: dict[str, Any],
    thread_active_frame: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """Inject previous active concept on expansion follow-up in MVP profile."""
    guard = dict(knowledge_answer_guard or {})
    knowledge_answer = (
        dict(guard.get("knowledge_answer", {}))
        if isinstance(guard.get("knowledge_answer"), dict)
        else {}
    )
    concept = str(knowledge_answer.get("concept", "") or "").strip().lower()
    previous = extract_last_active_concept(thread_active_frame)
    profile = normalize_dialogue_profile(dialogue_profile)
    expansion_requested = detect_expansion_request(user_message)

    if concept:
        return guard, concept

    if (
        profile == DIALOGUE_PROFILE_MVP_FREE
        and expansion_requested
        and previous
    ):
        knowledge_answer["needed"] = True
        knowledge_answer["concept"] = previous
        knowledge_answer["should_answer_directly"] = True
        knowledge_answer["kb_grounding_available"] = bool(
            knowledge_answer.get("kb_grounding_available", True)
        )
        reason = str(knowledge_answer.get("reason", "no_known_concept_question") or "")
        knowledge_answer["reason"] = (
            "followup_expansion_inherits_active_concept"
            if reason == "no_known_concept_question"
            else reason
        )
        guard["knowledge_answer"] = knowledge_answer
        return guard, previous

    return guard, previous


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())
