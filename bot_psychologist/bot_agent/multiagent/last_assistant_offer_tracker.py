"""Last assistant offer tracking for unified dialogue policy."""

from __future__ import annotations

import re
from typing import Any


LAST_ASSISTANT_OFFER_VERSION = "last_assistant_offer_v1"

_OFFER_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("explain_examples", ("на примере", "пример", "объясню", "объяснить")),
    ("adapt_technique", ("адапт", "подстро", "вариант", "сделаю мягче")),
    ("continue_topic", ("продолж", "разверну", "раскрою", "пойти дальше")),
    ("summarize", ("подвести итог", "суммир", "резюме")),
    ("shorten", ("коротко", "в двух словах", "одной фразой")),
    ("expand", ("подробно", "развернуто", "развёрнуто", "глубже")),
    ("practice", ("шаг", "упражн", "практик", "техник")),
]
_OFFER_OPEN_MARKERS = (
    "хочешь",
    "могу",
    "если хочешь",
    "могу предложить",
    "могу объяснить",
    "показать",
    "покажу",
    "готов показать",
    "готова показать",
    "предлагаю такой план",
    "как предпочитаешь дальше",
    "скажи, что выбрать",
    "выбери",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _offer_type_from_text(text: str) -> str:
    lowered = _normalize(text)
    if not lowered:
        return "none"
    for offer_type, markers in _OFFER_PATTERNS:
        if any(marker in lowered for marker in markers):
            return offer_type
    return "none"


def _summary(text: str, *, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", str(text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def build_last_assistant_offer_v1(
    *,
    previous_state: dict[str, Any] | None,
    previous_assistant_message: str,
    dialogue_pragmatics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = dict(previous_state or {})
    previous_text = str(previous_assistant_message or "").strip()

    if state.get("version") == LAST_ASSISTANT_OFFER_VERSION and str(state.get("offer_text_summary", "") or "").strip():
        stored_turn_index = int(state.get("turn_index", 0) or 0)
        return {
            "version": LAST_ASSISTANT_OFFER_VERSION,
            "offer_id": str(state.get("offer_id", "") or ""),
            "turn_index": stored_turn_index,
            "offer_type": str(state.get("offer_type", "none") or "none"),
            "offer_text_summary": str(state.get("offer_text_summary", "") or ""),
            "expected_user_reply": str(state.get("expected_user_reply", "") or "none"),
            "action_on_confirmation": str(state.get("action_on_confirmation", "none") or "none"),
            "is_open": bool(state.get("is_open", False)),
        }

    offer_type = _offer_type_from_text(previous_text)
    is_open = bool(previous_text) and any(marker in _normalize(previous_text) for marker in _OFFER_OPEN_MARKERS)
    if not is_open and bool(dialogue_pragmatics and dialogue_pragmatics.get("is_contextual_followup", False)):
        is_open = offer_type != "none"
    return {
        "version": LAST_ASSISTANT_OFFER_VERSION,
        "offer_id": "",
        "turn_index": 0,
        "offer_type": offer_type,
        "offer_text_summary": _summary(previous_text),
        "expected_user_reply": "yes_no_or_request" if is_open else "none",
        "action_on_confirmation": "answer_last_offer" if is_open else "none",
        "is_open": is_open,
    }


def update_last_assistant_offer_after_answer_v1(
    *,
    final_answer: str,
    turn_index: int,
) -> dict[str, Any]:
    text = str(final_answer or "").strip()
    offer_type = _offer_type_from_text(text)
    lowered = _normalize(text)
    is_open = any(marker in lowered for marker in _OFFER_OPEN_MARKERS) or (text.endswith("?") and offer_type != "none")
    offer_id = f"offer_turn_{turn_index:03d}_001" if is_open else ""
    return {
        "version": LAST_ASSISTANT_OFFER_VERSION,
        "offer_id": offer_id,
        "turn_index": int(turn_index),
        "offer_type": offer_type,
        "offer_text_summary": _summary(text),
        "expected_user_reply": "yes_no_or_request" if is_open else "none",
        "action_on_confirmation": "answer_last_offer" if is_open else "none",
        "is_open": is_open,
    }


__all__ = [
    "LAST_ASSISTANT_OFFER_VERSION",
    "build_last_assistant_offer_v1",
    "update_last_assistant_offer_after_answer_v1",
]
