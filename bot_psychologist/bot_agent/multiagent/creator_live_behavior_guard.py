"""Deterministic behavior guard helpers for creator-live calibration (HF4)."""

from __future__ import annotations

from typing import Any


REQUEST_TYPE_EXAMPLE = "example_request"
REQUEST_TYPE_EXPLAIN = "explain_request"
REQUEST_TYPE_PRACTICE = "practice_request"
REQUEST_TYPE_SUPPORT = "support_request"
REQUEST_TYPE_SAFETY = "safety_regulation_request"
REQUEST_TYPE_UNKNOWN = "unknown"

_EXAMPLE_MARKERS = (
    "\u043f\u0440\u0438\u043c\u0435\u0440",
    "\u043f\u0440\u0438\u0432\u0435\u0434\u0438 \u043f\u0440\u0438\u043c\u0435\u0440",
    "\u0438\u0437 \u0436\u0438\u0437\u043d\u0438",
    "\u043f\u043e\u043a\u0430\u0436\u0438 \u043d\u0430 \u043f\u0440\u0438\u043c\u0435\u0440\u0435",
    "\u0441 \u0440\u043e\u0434\u0438\u0442\u0435\u043b\u0435\u043c",
    "\u0441 \u043f\u0430\u0440\u0442\u043d\u0435\u0440\u043e\u043c",
    "\u0441 \u043f\u0430\u0440\u0442\u043d\u0435\u0440\u0451\u043c",
    "example",
    "real life example",
)
_EXPLAIN_MARKERS = (
    "\u043e\u0431\u044a\u044f\u0441\u043d\u0438",
    "\u0447\u0442\u043e \u0442\u0430\u043a\u043e\u0435",
    "\u0432 \u0447\u0435\u043c",
    "\u043a\u0430\u043a \u044d\u0442\u043e",
    "\u043a\u0430\u043a \u044d\u0442\u043e \u043f\u0440\u0438\u043c\u0435\u043d",
    "explain",
    "what is",
)
_PRACTICE_REQUEST_MARKERS = (
    "\u043f\u0440\u0430\u043a\u0442\u0438\u043a",
    "\u0443\u043f\u0440\u0430\u0436\u043d",
    "\u0442\u0435\u0445\u043d\u0438\u043a",
    "\u0434\u044b\u0445\u0430\u043d\u0438",
    "\u043a\u0430\u043a \u0443\u0441\u043f\u043e\u043a\u043e",
    "\u043f\u043e\u043c\u043e\u0433\u0438 \u0443\u0441\u043f\u043e\u043a\u043e\u0438\u0442\u044c\u0441\u044f",
    "practice",
    "exercise",
    "breath",
    "calm down",
)
_SUPPORT_MARKERS = (
    "\u043f\u043e\u0434\u0434\u0435\u0440\u0436",
    "\u0440\u044f\u0434\u043e\u043c",
    "\u043c\u043d\u0435 \u0442\u044f\u0436\u0435\u043b\u043e",
    "\u043c\u0435\u043d\u044f \u043d\u0430\u043a\u0440\u044b\u043b\u043e",
    "help me",
    "support",
    "stay with me",
)
_SAFETY_REGULATION_MARKERS = (
    "\u043f\u0440\u044f\u043c\u043e \u0441\u0435\u0439\u0447\u0430\u0441",
    "\u043e\u0447\u0435\u043d\u044c \u0442\u0440\u0435\u0432\u043e\u0436\u043d\u043e",
    "\u043f\u0430\u043d\u0438\u043a\u0430",
    "\u043d\u0435 \u043c\u043e\u0433\u0443 \u0443\u0441\u043f\u043e\u043a\u043e\u0438\u0442\u044c\u0441\u044f",
    "\u0441\u0435\u0439\u0447\u0430\u0441 \u043f\u043b\u043e\u0445\u043e",
    "can't calm down",
    "panic",
    "right now",
    "urgent",
)
_PRACTICE_REJECTION_MARKERS = (
    "\u043d\u0435 \u043f\u0440\u0430\u043a\u0442\u0438\u043a",
    "\u043d\u0435 \u0443\u043f\u0440\u0430\u0436\u043d",
    "\u043d\u0435 \u0442\u0435\u0445\u043d\u0438\u043a",
    "\u043f\u0440\u043e\u0441\u0442\u043e \u043e\u0431\u044a\u044f\u0441\u043d\u0438",
    "\u043d\u0435 \u0434\u044b\u0445\u0430\u043d\u0438",
    "\u0445\u0432\u0430\u0442\u0438\u0442 \u0434\u044b\u0445\u0430\u043d\u0438",
    "\u0431\u0435\u0437 \u043f\u0440\u0430\u043a\u0442\u0438\u043a",
    "\u0431\u0435\u0437 \u0443\u043f\u0440\u0430\u0436\u043d",
    "without practice",
    "no breathing",
)
_BODY_ACTION_MARKERS = (
    "\u0441\u0434\u0435\u043b\u0430\u0439 \u0432\u0434\u043e\u0445",
    "\u0441\u0434\u0435\u043b\u0430\u0439\u0442\u0435 \u0432\u0434\u043e\u0445",
    "\u0432\u0434\u043e\u0445\u043d\u0438",
    "\u0432\u0434\u043e\u0445",
    "\u0432\u044b\u0434\u043e\u0445",
    "\u0434\u044b\u0448\u0438",
    "\u0434\u044b\u0445\u0430\u043d\u0438\u0435",
    "\u043f\u043e\u0447\u0443\u0432\u0441\u0442\u0432\u0443\u0439 \u0442\u0435\u043b\u043e",
    "\u0440\u0430\u0441\u0441\u043b\u0430\u0431\u044c \u043f\u043b\u0435\u0447\u0438",
    "\u043f\u043e\u043b\u043e\u0436\u0438 \u0440\u0443\u043a\u0443",
    "body action",
    "take a breath",
)


def _safe_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_text(text)
    return any(marker in lowered for marker in markers)


def detect_request_type_v1(user_message: str) -> str:
    text = _safe_text(user_message)
    if not text:
        return REQUEST_TYPE_UNKNOWN
    if _contains_any(text, _SAFETY_REGULATION_MARKERS):
        return REQUEST_TYPE_SAFETY
    if _contains_any(text, _EXAMPLE_MARKERS):
        return REQUEST_TYPE_EXAMPLE
    if _contains_any(text, _EXPLAIN_MARKERS):
        return REQUEST_TYPE_EXPLAIN
    if _contains_any(text, _PRACTICE_REQUEST_MARKERS):
        return REQUEST_TYPE_PRACTICE
    if _contains_any(text, _SUPPORT_MARKERS):
        return REQUEST_TYPE_SUPPORT
    return REQUEST_TYPE_UNKNOWN


def detect_practice_rejection_v1(text: str) -> bool:
    return _contains_any(text, _PRACTICE_REJECTION_MARKERS)


def detect_body_action_marker_v1(text: str) -> bool:
    return _contains_any(text, _BODY_ACTION_MARKERS)


def collect_recent_turn_texts_v1(
    recent_turns: list[Any],
    *,
    last_n: int = 3,
    assistant_only: bool = False,
) -> list[str]:
    if not isinstance(recent_turns, list):
        return []
    texts: list[str] = []
    for raw in recent_turns[-max(1, int(last_n)) :]:
        role = getattr(raw, "role", None)
        content = getattr(raw, "content", None)
        if isinstance(raw, dict):
            role = raw.get("role", role)
            content = raw.get("content", content)
        if assistant_only and str(role or "").lower() != "assistant":
            continue
        value = str(content or "").strip()
        if value:
            texts.append(value)
    return texts


def evaluate_anti_regulate_loop_v1(
    *,
    user_message: str,
    recent_turn_texts: list[str],
    safety_active: bool,
    response_mode: str,
    suggested_writer_move: str,
) -> dict[str, Any]:
    request_type = detect_request_type_v1(user_message)
    user_rejected_practice = (
        detect_practice_rejection_v1(user_message)
        or any(detect_practice_rejection_v1(text) for text in list(recent_turn_texts or []))
    )
    recent_body_action_seen = any(
        detect_body_action_marker_v1(text) for text in list(recent_turn_texts or [])
    )
    practice_marker_hit = _contains_any(user_message, _PRACTICE_REQUEST_MARKERS)
    explicit_regulation_request = (
        request_type == REQUEST_TYPE_SAFETY
        or (practice_marker_hit and not detect_practice_rejection_v1(user_message))
    )
    suppress = (
        not safety_active
        and not explicit_regulation_request
        and (
            request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}
            or user_rejected_practice
            or recent_body_action_seen
        )
        and (response_mode == "regulate" or suggested_writer_move == "regulate_first")
    )
    reasons: list[str] = []
    if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}:
        reasons.append("user_requested_example_or_explanation")
    if user_rejected_practice:
        reasons.append("user_rejected_practice")
    if recent_body_action_seen:
        reasons.append("recent_body_action_detected")
    if safety_active:
        reasons.append("safety_active_override")
    if explicit_regulation_request:
        reasons.append("explicit_regulation_request")
    return {
        "version": "anti_regulate_loop_v1",
        "request_type": request_type,
        "user_rejected_practice": user_rejected_practice,
        "recent_body_action_detected": recent_body_action_seen,
        "explicit_regulation_request": explicit_regulation_request,
        "practice_or_regulate_should_be_suppressed": suppress,
        "reasons": reasons,
    }


__all__ = [
    "REQUEST_TYPE_EXAMPLE",
    "REQUEST_TYPE_EXPLAIN",
    "REQUEST_TYPE_PRACTICE",
    "REQUEST_TYPE_SUPPORT",
    "REQUEST_TYPE_SAFETY",
    "REQUEST_TYPE_UNKNOWN",
    "detect_request_type_v1",
    "detect_practice_rejection_v1",
    "detect_body_action_marker_v1",
    "collect_recent_turn_texts_v1",
    "evaluate_anti_regulate_loop_v1",
]
