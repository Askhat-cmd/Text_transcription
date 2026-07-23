from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .writer_agent_constants import _contains_any


EnforceBlockBPart1Outcome = Literal[
    "not_matched",
    "known_concept_prefirst_correlation",
    "known_concept_prefirst_neurostalking",
    "known_concept_prefirst_self_realization",
    "no_question_one_step",
    "no_question_short_support",
    "no_question_safety_grounding",
    "no_question_known_concept_correlation",
    "no_question_known_concept_neurostalking",
    "no_question_default_strip",
    "question_marker_one_step",
    "question_marker_short_support",
    "question_marker_safety_grounding",
    "question_marker_close_gently",
    "question_marker_default",
    "none_policy_one_step",
    "none_policy_mechanism_repair",
    "repair_misalignment",
    "practice_forbidden_unsolicited_repair",
]


@dataclass(frozen=True)
class EnforceBlockBPart1Result:
    outcome: EnforceBlockBPart1Outcome
    return_text: Optional[str] = None
    last_debug_patch: dict[str, Any] = field(default_factory=dict)


def _classify_enforce_block_b_part1(
    *,
    text: str,
    user_message: str,
    lowered_user: str,
    lowered_text: str,
    concept: str,
    should_answer_directly: bool,
    asks_define_known_term: bool,
    has_external_surveillance_frame: bool,
    planner_question_policy: str,
    planner_next_move: str,
    planner_answer_shape: str,
    planner_practice_policy: str,
    has_question: bool,
    has_unsolicited_practice: bool,
) -> EnforceBlockBPart1Result:
    if should_answer_directly and (asks_define_known_term or has_external_surveillance_frame):
        if "самореализац" in lowered_user and ("коррелир" in lowered_user or "связан" in lowered_user):
            return EnforceBlockBPart1Result(outcome="known_concept_prefirst_correlation")
        if concept == "нейросталкинг":
            return EnforceBlockBPart1Result(outcome="known_concept_prefirst_neurostalking")
        if concept == "самореализация":
            return EnforceBlockBPart1Result(outcome="known_concept_prefirst_self_realization")

    if planner_question_policy == "none" and has_question:
        if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
            return EnforceBlockBPart1Result(outcome="no_question_one_step")
        if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
            return EnforceBlockBPart1Result(outcome="no_question_short_support")
        if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
            return EnforceBlockBPart1Result(outcome="no_question_safety_grounding")
        if planner_next_move == "answer_known_concept":
            if "самореализац" in lowered_user and "нейросталкинг" in lowered_user:
                return EnforceBlockBPart1Result(outcome="no_question_known_concept_correlation")
            if "нейросталкинг" in lowered_user:
                return EnforceBlockBPart1Result(outcome="no_question_known_concept_neurostalking")
        return EnforceBlockBPart1Result(
            outcome="no_question_default_strip",
            return_text=re.sub(r"\s*\?+\s*", ". ", text).strip(),
        )

    if planner_question_policy == "none" and _contains_any(
        lowered_text, ("что именно", "почему", "как ты", "можешь ли", "хочешь")
    ):
        if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
            return EnforceBlockBPart1Result(outcome="question_marker_one_step")
        if planner_next_move == "give_short_support":
            return EnforceBlockBPart1Result(outcome="question_marker_short_support")
        if planner_next_move == "stabilize_safety":
            return EnforceBlockBPart1Result(outcome="question_marker_safety_grounding")
        if planner_next_move == "close_gently":
            return EnforceBlockBPart1Result(outcome="question_marker_close_gently")
        return EnforceBlockBPart1Result(outcome="question_marker_default")

    if planner_question_policy == "none":
        if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
            return EnforceBlockBPart1Result(outcome="none_policy_one_step")
        if planner_next_move == "deepen_mechanism" or planner_answer_shape == "mechanism_explanation":
            return EnforceBlockBPart1Result(outcome="none_policy_mechanism_repair")

    if planner_next_move == "repair_misalignment":
        has_repair_forbidden = _contains_any(lowered_text, ("практик", "упражн", "таймер", "шаг"))
        if has_question or has_repair_forbidden or len(text) > 480:
            return EnforceBlockBPart1Result(outcome="repair_misalignment")

    if planner_practice_policy == "forbidden" and has_unsolicited_practice:
        return EnforceBlockBPart1Result(
            outcome="practice_forbidden_unsolicited_repair",
            last_debug_patch={"template_leakage_repair_deferred_to_gate": True},
        )

    return EnforceBlockBPart1Result(outcome="not_matched")
