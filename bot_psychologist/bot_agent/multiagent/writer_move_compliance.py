"""Deterministic writer move constraints and compliance checks."""

from __future__ import annotations

import re
from typing import Any

from .contracts.diagnostic_card import DiagnosticCard


WRITER_MOVE_INSTRUCTIONS_VERSION = "writer_move_instructions_v1"
WRITER_MOVE_COMPLIANCE_TRACE_VERSION = "writer_move_compliance_trace_v1"

_MULTI_STEP_MARKERS = (
    " и ",
    " затем ",
    " потом ",
    " afterwards ",
    " then ",
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _count_sentences(text: str) -> int:
    chunks = re.findall(r"[^.!?]+[.!?]?", text)
    return len([chunk for chunk in chunks if chunk.strip()])


def _count_questions(text: str) -> int:
    return text.count("?")


def _contains_numbered_list(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*\d+[\.)]\s+", text))


def _base_instruction(move: str) -> dict[str, Any]:
    return {
        "version": WRITER_MOVE_INSTRUCTIONS_VERSION,
        "move": move,
        "max_sentences": 5,
        "max_questions": 1,
        "style": "brief_supportive",
        "must_do": ["validate_current_state", "stay_close_to_user_words"],
        "must_not_do": ["do_not_analyze_deeply"],
    }


def build_writer_move_instructions_v1(diagnostic_card: DiagnosticCard | None) -> dict[str, Any]:
    """Map diagnostic card into deterministic Writer output constraints."""
    if diagnostic_card is None:
        return _base_instruction("validate_briefly")

    move = str(diagnostic_card.suggested_writer_move or "validate_briefly").strip() or "validate_briefly"
    risk_flags = [str(item) for item in list(diagnostic_card.risk_flags or [])]
    instructions = _base_instruction(move)

    if move == "safe_override":
        instructions.update(
            {
                "max_sentences": 3,
                "max_questions": 0,
                "style": "short_direct_safety",
                "must_do": [
                    "prioritize_safety_protocol",
                    "use_short_direct_support",
                ],
                "must_not_do": [
                    "do_not_explore",
                    "do_not_analyze",
                ],
            }
        )
    elif move == "regulate_first":
        instructions.update(
            {
                "max_sentences": 4,
                "max_questions": 0,
                "style": "brief_low_pressure",
                "must_do": [
                    "offer_one_simple_body_action",
                    "keep_language_short",
                    "reduce_pressure",
                ],
                "must_not_do": [
                    "do_not_analyze",
                    "do_not_explain_pattern",
                    "do_not_ask_followup_question",
                    "do_not_offer_multiple_steps",
                ],
            }
        )
    elif move == "validate_briefly":
        instructions.update(
            {
                "max_sentences": 4,
                "max_questions": 1,
                "style": "brief_validation",
                "must_do": [
                    "validate_current_state",
                    "stay_close_to_user_words",
                ],
                "must_not_do": [
                    "do_not_analyze_deeply",
                    "do_not_give_advice",
                ],
            }
        )
        if "low_resource" in risk_flags:
            instructions["max_questions"] = 0
            instructions["must_not_do"] = list(instructions["must_not_do"]) + [
                "do_not_ask_followup_question"
            ]
    elif move == "offer_one_micro_step":
        instructions.update(
            {
                "max_sentences": 5,
                "max_questions": 0,
                "style": "concrete_micro_step",
                "must_do": [
                    "offer_one_executable_micro_step",
                    "include_time_or_start_condition",
                ],
                "must_not_do": [
                    "do_not_offer_list",
                    "do_not_expand_theory",
                ],
            }
        )
    elif move == "give_concrete_example":
        instructions.update(
            {
                "max_sentences": 8,
                "max_questions": 1,
                "style": "concrete_contextual_example",
                "must_do": [
                    "give_one_concrete_life_example",
                    "use_user_requested_context",
                    "avoid_practice_instruction",
                    "avoid_breathing_instruction",
                    "connect_example_to_current_thread",
                ],
                "must_not_do": [
                    "do_not_offer_body_action",
                    "do_not_turn_into_lecture",
                    "do_not_open_multiple_threads",
                    "do_not_ignore_user_rejected_practice",
                ],
            }
        )
    elif move == "reflect_pattern_once":
        instructions.update(
            {
                "max_sentences": 6,
                "max_questions": 1,
                "style": "single_pattern_reflection",
                "must_do": [
                    "name_one_repeated_pattern_gently",
                    "connect_to_recent_context",
                    "return_authority_to_user",
                ],
                "must_not_do": [
                    "do_not_list_multiple_hypotheses",
                    "do_not_rewrite_full_history",
                    "do_not_over_explain",
                ],
            }
        )
    elif move == "clarify_one_point":
        instructions.update(
            {
                "max_sentences": 5,
                "max_questions": 1,
                "style": "focused_clarification",
                "must_do": [
                    "reflect_one_key_point",
                    "ask_one_specific_question",
                ],
                "must_not_do": [
                    "do_not_open_multiple_threads",
                ],
            }
        )
    elif move == "explore_carefully":
        instructions.update(
            {
                "max_sentences": 6,
                "max_questions": 1,
                "style": "careful_exploration",
                "must_do": [
                    "offer_one_hypothesis_as_hypothesis",
                    "avoid_strong_interpretation",
                ],
                "must_not_do": [
                    "do_not_turn_into_lecture",
                    "do_not_add_second_hypothesis",
                ],
            }
        )

    instructions["must_do"] = _dedupe(
        [str(item) for item in list(instructions.get("must_do", []) or [])]
    )
    instructions["must_not_do"] = _dedupe(
        [str(item) for item in list(instructions.get("must_not_do", []) or [])]
        + [str(item) for item in list(getattr(diagnostic_card, "avoid_list", []) or [])]
    )
    instructions["risk_flags"] = risk_flags
    return instructions


def build_writer_move_compliance_trace_v1(
    *,
    final_answer: str,
    instructions: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate final answer against deterministic writer-move constraints."""
    normalized = str(final_answer or "").strip()
    move = str(instructions.get("move", "validate_briefly") or "validate_briefly")
    raw_max_sentences = instructions.get("max_sentences", 5)
    raw_max_questions = instructions.get("max_questions", 1)
    try:
        max_sentences = int(raw_max_sentences)
    except (TypeError, ValueError):
        max_sentences = 5
    try:
        max_questions = int(raw_max_questions)
    except (TypeError, ValueError):
        max_questions = 1
    sentence_count = _count_sentences(normalized)
    question_count = _count_questions(normalized)
    contains_numbered_list = _contains_numbered_list(normalized)
    lowered = normalized.lower()
    violations: list[str] = []

    if sentence_count > max_sentences:
        violations.append("too_many_sentences")
    if question_count > max_questions:
        violations.append("too_many_questions")
    if contains_numbered_list and "do_not_offer_list" in list(instructions.get("must_not_do", []) or []):
        violations.append("contains_numbered_list")
    if "do_not_offer_multiple_steps" in list(instructions.get("must_not_do", []) or []):
        marker_hits = sum(1 for marker in _MULTI_STEP_MARKERS if marker in lowered)
        if marker_hits >= 2:
            violations.append("possible_multiple_steps")
    if move == "reflect_pattern_once" and sentence_count > 6:
        violations.append("over_explained_reflection")
    if move == "regulate_first" and question_count > 0:
        violations.append("regulate_should_not_ask_question")

    return {
        "version": WRITER_MOVE_COMPLIANCE_TRACE_VERSION,
        "move": move,
        "max_sentences": max_sentences,
        "max_questions": max_questions,
        "sentence_count": sentence_count,
        "question_count": question_count,
        "contains_numbered_list": contains_numbered_list,
        "violations": _dedupe(violations),
        "risk_flags": [str(item) for item in list(instructions.get("risk_flags", []) or [])],
    }
