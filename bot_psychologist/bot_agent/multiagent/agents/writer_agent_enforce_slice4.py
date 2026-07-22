from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional


Slice4Outcome = Literal[
    "not_matched",
    "literal_markdown_echo_mismatch",
    "acknowledge_style_preference_repair",
    "repair_and_answer_last_question_repair",
    "answer_last_offer_repair",
    "answer_knowledge_or_direct_repair",
]


@dataclass(frozen=True)
class EnforceSlice4Result:
    outcome: Slice4Outcome
    last_debug_patch: Optional[dict[str, Any]] = None
    return_text: Optional[str] = None
    defer_signal: Optional[str] = None
    defer_must_answer: Optional[str] = None


def _classify_enforce_slice4_obligation_repairs_and_echo(
    *,
    text: str,
    user_message: str,
    lowered_text: str,
    answer_obligation: str,
    literal_markdown_echo: str,
    concept_question: bool,
    last_direct_question: str,
    last_offer_summary: str,
    offer_repair_context: str,
) -> EnforceSlice4Result:
    if literal_markdown_echo:
        normalized_requested = literal_markdown_echo.strip()
        normalized_response = text.strip()
        if normalized_response != normalized_requested:
            return EnforceSlice4Result(
                outcome="literal_markdown_echo_mismatch",
                last_debug_patch={
                    "format_request_repair_applied": True,
                    "final_answer_shape": "literal_markdown_echo",
                },
                return_text=normalized_requested,
            )

    if answer_obligation == "acknowledge_style_preference_then_answer" and (
        "расскажи больше" in lowered_text or len(text) < 140
    ):
        if concept_question:
            return EnforceSlice4Result(
                outcome="acknowledge_style_preference_repair",
                defer_signal="style_preference_direct_answer_repair",
                defer_must_answer="known_concept_question",
            )

    if answer_obligation == "repair_and_answer_last_question" and (
        "сейчас полезнее прямое объяснение механизма" in lowered_text or len(text) < 180
    ):
        target = last_direct_question or user_message
        if "нейросталкинг" in target.lower():
            return EnforceSlice4Result(
                outcome="repair_and_answer_last_question_repair",
                defer_signal="repair_answer_last_question_repair",
                defer_must_answer=target,
            )

    if answer_obligation == "answer_last_offer" and (
        any(marker in lowered_text for marker in ("подтверди", "если хочешь", "могу так сделать"))
        or any(marker in lowered_text for marker in ("предлагаю такой план", "хотите, чтобы", "сначала"))
        or "после подтверждения" in lowered_text
        or ("могу так сделать" in last_offer_summary.lower() and len(text) < 500)
        or (
            any(color in offer_repair_context for color in ("красн", "оранж", "зелен"))
            and not all(color in lowered_text for color in ("красн", "оранж", "зелен"))
        )
    ):
        if any(color in offer_repair_context for color in ("красн", "оранж", "зелен")):
            return EnforceSlice4Result(
                outcome="answer_last_offer_repair",
                defer_signal="answer_last_offer_repair",
                defer_must_answer=last_offer_summary or last_direct_question or "last_assistant_offer",
            )

    if answer_obligation in {"answer_knowledge_question", "answer_direct_question"} and (
        "сейчас полезнее прямое объяснение механизма" in lowered_text or len(text) < 140
    ):
        if concept_question:
            return EnforceSlice4Result(
                outcome="answer_knowledge_or_direct_repair",
                defer_signal="knowledge_direct_answer_repair",
                defer_must_answer="known_concept_question",
            )

    return EnforceSlice4Result(outcome="not_matched")
