"""Tracks unanswered direct user questions across turns."""

from __future__ import annotations

from typing import Any


UNANSWERED_QUESTION_TRACKER_VERSION = "unanswered_question_tracker_v1"

_QUESTION_ACTS = {
    "direct_question": "direct_question",
    "knowledge_question": "direct_knowledge_question",
    "concrete_situation_question": "concrete_situation_question",
    "practice_request": "practice_request",
}


def build_unanswered_question_state_v1(
    *,
    previous_state: dict[str, Any] | None,
    user_message: str,
    dialogue_act_resolution: dict[str, Any] | None,
    turn_index: int,
) -> dict[str, Any]:
    previous = dict(previous_state or {})
    act = str((dialogue_act_resolution or {}).get("dialogue_act", "unknown") or "unknown")

    if act in _QUESTION_ACTS:
        return {
            "version": UNANSWERED_QUESTION_TRACKER_VERSION,
            "last_direct_user_question": str(user_message or "").strip(),
            "turn_index": int(turn_index),
            "answer_required": True,
            "answer_status": "pending",
            "reason": _QUESTION_ACTS[act],
        }

    if act == "repair_complaint" and str(previous.get("last_direct_user_question", "") or "").strip():
        return {
            "version": UNANSWERED_QUESTION_TRACKER_VERSION,
            "last_direct_user_question": str(previous.get("last_direct_user_question", "") or ""),
            "turn_index": int(previous.get("turn_index", turn_index) or turn_index),
            "answer_required": True,
            "answer_status": str(previous.get("answer_status", "pending") or "pending"),
            "reason": str(previous.get("reason", "direct_question") or "direct_question"),
        }

    if previous:
        return {
            "version": UNANSWERED_QUESTION_TRACKER_VERSION,
            "last_direct_user_question": str(previous.get("last_direct_user_question", "") or ""),
            "turn_index": int(previous.get("turn_index", 0) or 0),
            "answer_required": bool(previous.get("answer_required", False)),
            "answer_status": str(previous.get("answer_status", "answered") or "answered"),
            "reason": str(previous.get("reason", "") or ""),
        }

    return {
        "version": UNANSWERED_QUESTION_TRACKER_VERSION,
        "last_direct_user_question": "",
        "turn_index": int(turn_index),
        "answer_required": False,
        "answer_status": "answered",
        "reason": "",
    }


def update_unanswered_question_state_after_answer_v1(
    *,
    current_state: dict[str, Any] | None,
    answer_obligation_resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    state = dict(current_state or {})
    if not state:
        return {
            "version": UNANSWERED_QUESTION_TRACKER_VERSION,
            "last_direct_user_question": "",
            "turn_index": 0,
            "answer_required": False,
            "answer_status": "answered",
            "reason": "",
        }
    obligation = str((answer_obligation_resolution or {}).get("answer_obligation", "") or "")
    if obligation in {
        "answer_direct_question",
        "answer_knowledge_question",
        "answer_concrete_situation",
        "provide_one_bounded_practice",
        "repair_and_answer_last_question",
        "acknowledge_style_preference_then_answer",
        "answer_last_offer",
    }:
        updated = dict(state)
        updated["answer_required"] = False
        updated["answer_status"] = "repaired" if obligation == "repair_and_answer_last_question" else "answered"
        return updated
    return state


__all__ = [
    "UNANSWERED_QUESTION_TRACKER_VERSION",
    "build_unanswered_question_state_v1",
    "update_unanswered_question_state_after_answer_v1",
]
