from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from ..active_line import starts_with_mechanical_revoicing
from .writer_agent_constants import _contains_any


EnforceBlockBPart2Outcome = Literal[
    "not_matched",
    "mechanism_explanation_repair_g7",
    "one_step_g8",
    "first_item_extraction_g9",
    "sentence_parts_one_step_g9",
    "question_marker_one_step_g9",
    "no_step_marker_one_step_g9",
    "safety_grounding_g10",
    "active_line_correction_repair_g10",
    "active_line_mechanism_repair_g10",
    "practice_suppression_meaning_repair_g10",
    "active_line_revoicing_correction_repair_g11",
    "active_line_revoicing_mechanism_repair_g11",
    "revoicing_strip_g11",
    "known_concept_correlation_repair_g12",
    "known_concept_neurostalking_repair_g12",
    "known_concept_self_realization_repair_g12",
]


@dataclass(frozen=True)
class EnforceBlockBPart2Result:
    outcome: EnforceBlockBPart2Outcome
    return_text: Optional[str] = None


def _classify_enforce_block_b_part2(
    *,
    text: str,
    user_message: str,
    lowered_user: str,
    lowered_text: str,
    planner_next_move: str,
    planner_question_policy: str,
    planner_answer_shape: str,
    planner_practice_policy: str,
    user_mechanism_request: bool,
    user_requests_no_question: bool,
    user_requests_no_practice: bool,
    has_question: bool,
    has_unsolicited_practice: bool,
    user_step_request: bool,
    active_line_intent: str,
    active_line_practice_suppression: bool,
    active_line_should_offer_practice: bool,
    active_line_repair_mode: bool,
    active_line_revoicing_allowed: bool,
) -> EnforceBlockBPart2Result:
    if (
        (planner_next_move == "deepen_mechanism" or user_mechanism_request)
        and (planner_question_policy == "none" or user_requests_no_question)
        and (len(text) > 700 or has_question or has_unsolicited_practice or user_requests_no_practice)
    ):
        return EnforceBlockBPart2Result(outcome="mechanism_explanation_repair_g7")

    if planner_answer_shape == "one_step" or planner_next_move == "give_direct_step":
        return EnforceBlockBPart2Result(outcome="one_step_g8")

    if planner_answer_shape == "one_step" or user_step_request or active_line_intent == "ask_for_direct_step":
        list_like = bool(re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", text))
        if list_like:
            first_item = re.search(r"(?:[-*•]|\d+[.)])\s+(.+)", text)
            if first_item:
                return EnforceBlockBPart2Result(
                    outcome="first_item_extraction_g9",
                    return_text=first_item.group(1).strip(),
                )
        sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        if len(sentence_parts) > 2:
            return EnforceBlockBPart2Result(outcome="sentence_parts_one_step_g9")
        if planner_question_policy == "none" and _contains_any(
            lowered_text,
            (
                "хочешь",
                "хочется",
                "можешь",
                "уточни",
                "попробу",
                "какой",
                "что выбрать",
            ),
        ):
            return EnforceBlockBPart2Result(outcome="question_marker_one_step_g9")
        has_step_marker = _contains_any(lowered_text, ("сделай", "начни", "открой", "выбери", "напиши", "шаг"))
        if not has_step_marker:
            return EnforceBlockBPart2Result(outcome="no_step_marker_one_step_g9")

    if active_line_practice_suppression and not active_line_should_offer_practice and has_unsolicited_practice:
        if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
            return EnforceBlockBPart2Result(outcome="safety_grounding_g10")
        if active_line_intent == "correction_of_bot" or active_line_repair_mode:
            return EnforceBlockBPart2Result(outcome="active_line_correction_repair_g10")
        if active_line_intent == "understand_mechanism":
            return EnforceBlockBPart2Result(outcome="active_line_mechanism_repair_g10")
        return EnforceBlockBPart2Result(outcome="practice_suppression_meaning_repair_g10")

    if not active_line_revoicing_allowed and starts_with_mechanical_revoicing(text):
        if active_line_intent == "correction_of_bot" or active_line_repair_mode:
            return EnforceBlockBPart2Result(outcome="active_line_revoicing_correction_repair_g11")
        if active_line_intent == "understand_mechanism":
            return EnforceBlockBPart2Result(outcome="active_line_revoicing_mechanism_repair_g11")
        parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            return EnforceBlockBPart2Result(
                outcome="revoicing_strip_g11",
                return_text=parts[1].strip(),
            )

    if planner_next_move == "answer_known_concept" and planner_practice_policy == "forbidden":
        if "самореализац" in lowered_user and "нейросталкинг" in lowered_user:
            return EnforceBlockBPart2Result(outcome="known_concept_correlation_repair_g12")
        if "нейросталкинг" in lowered_user:
            return EnforceBlockBPart2Result(outcome="known_concept_neurostalking_repair_g12")
        if "самореализац" in lowered_user:
            return EnforceBlockBPart2Result(outcome="known_concept_self_realization_repair_g12")

    return EnforceBlockBPart2Result(outcome="not_matched")
