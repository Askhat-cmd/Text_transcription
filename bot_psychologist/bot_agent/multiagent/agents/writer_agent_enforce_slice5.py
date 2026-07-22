from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

from .writer_agent_constants import _contains_any


Slice5Outcome = Literal[
    "not_matched",
    "greeting_path",
    "low_resource_no_practice",
    "thanks_close",
    "safety_priority_has_question",
    "give_short_support_primary",
    "give_short_support_len_or_flags",
    "stabilize_safety_len_or_question",
    "stabilize_safety_markers",
    "close_gently",
    "give_short_support_markers",
    "clarify_one_point_zero_questions",
    "clarify_one_point_multi_questions",
    "clarify_one_point_long",
    "user_repair_signal",
]


@dataclass(frozen=True)
class EnforceSlice5Result:
    outcome: Slice5Outcome
    return_text: Optional[str] = None


def _classify_enforce_slice5_block_a(
    *,
    text: str,
    user_message: str,
    lowered_user: str,
    lowered_text: str,
    practice_allowed: bool,
    should_answer_directly: bool,
    is_greeting: bool,
    has_unsolicited_practice: bool,
    has_question: bool,
    active_line_intent: str,
    planner_safety_priority: bool,
    planner_next_move: str,
    planner_answer_shape: str,
    user_repair_signal: bool,
    low_resource_no_practice_markers: tuple[str, ...],
) -> EnforceSlice5Result:
    if not practice_allowed and not should_answer_directly and (is_greeting or has_unsolicited_practice):
        return EnforceSlice5Result(outcome="greeting_path")

    if _contains_any(lowered_user, low_resource_no_practice_markers):
        if has_unsolicited_practice or len(text) > 280 or "?" in text:
            return EnforceSlice5Result(outcome="low_resource_no_practice")

    if active_line_intent == "thanks_close" and (
        has_unsolicited_practice
        or _contains_any(lowered_text, ("шаг", "давай сделаем", "предложу еще"))
    ):
        return EnforceSlice5Result(outcome="thanks_close")

    if planner_safety_priority and has_question:
        return EnforceSlice5Result(outcome="safety_priority_has_question")

    if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
        return EnforceSlice5Result(outcome="give_short_support_primary")

    if planner_next_move == "give_short_support" and (len(text) > 260 or has_question or has_unsolicited_practice):
        return EnforceSlice5Result(outcome="give_short_support_len_or_flags")

    if planner_next_move == "stabilize_safety" and (len(text) > 320 or has_question):
        return EnforceSlice5Result(outcome="stabilize_safety_len_or_question")

    if planner_next_move == "stabilize_safety" and _contains_any(
        lowered_text,
        ("механизм", "прогнозирован", "контрол", "паттерн", "драйвер", "до начала действия"),
    ):
        return EnforceSlice5Result(outcome="stabilize_safety_markers")

    if planner_next_move == "close_gently" and (
        has_question
        or has_unsolicited_practice
        or _contains_any(lowered_text, ("новый шаг", "давай продолжим", "в следующий раз разберем"))
    ):
        return EnforceSlice5Result(outcome="close_gently")

    if planner_next_move == "give_short_support" and _contains_any(
        lowered_text,
        ("механизм", "теория", "стратегия", "прогнозирован", "контрол", "паттерн"),
    ):
        return EnforceSlice5Result(outcome="give_short_support_markers")

    if planner_next_move == "clarify_one_point":
        question_count = text.count("?")
        if question_count == 0:
            return EnforceSlice5Result(outcome="clarify_one_point_zero_questions")
        if question_count > 1:
            first = text.split("?")[0].strip()
            return EnforceSlice5Result(
                outcome="clarify_one_point_multi_questions",
                return_text=(first + "?").strip(),
            )
        if len(text) > 320:
            return EnforceSlice5Result(outcome="clarify_one_point_long")

    if user_repair_signal:
        return EnforceSlice5Result(outcome="user_repair_signal")

    return EnforceSlice5Result(outcome="not_matched")
