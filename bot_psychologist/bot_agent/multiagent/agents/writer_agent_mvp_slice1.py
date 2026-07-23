from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .writer_agent_fallback_helpers import _strip_optional_followup_invitation
from ..stale_stub_detector import detect_stale_stub
import re


MvpPart1Outcome = Literal[
    "not_matched",
    "repair_answer_last_question",
    "repair_user_dissatisfaction",
    "contextual_followup_short_phrase",
    "contextual_followup_example",
    "contextual_followup_direct",
    "safety_grounding_literal",
    "safety_grounding_passthrough",
    "sanitized_direct_no_forced_practice",
    "one_step",
    "structured_summary",
    "sarcasm_negative_feedback_repair",
    "direct_concrete_request_repair",
    "direct_no_forced_question",
    "practice_forbidden_sanitized",
    "practice_forbidden_repair_needed",
    "practice_forbidden_repair_default",
]


@dataclass(frozen=True)
class MvpPart1Result:
    outcome: MvpPart1Outcome
    updated_text: str
    updated_lowered_text: str
    return_text: Optional[str] = None
    computed_target: Optional[str] = None
    last_debug_patch: dict[str, Any] = field(default_factory=dict)


def _classify_mvp_part1(
    *,
    text: str,
    lowered_text: str,
    user_message: str,
    answer_obligation: str,
    last_offer_summary: str,
    last_direct_question: str,
    pragmatics_repair_dissatisfaction: bool,
    pragmatics_contextual_followup: bool,
    pragmatics_should_not_reconfirm: bool,
    pragmatics_offer_type: str,
    planner_safety_priority: bool,
    planner_next_move: str,
    planner_answer_shape: str,
    has_question: bool,
    canned_step_disallowed: bool,
    user_step_request: bool,
    summary_request: bool,
    sarcasm_or_negative_feedback: bool,
    direct_concrete_request: bool,
    explicit_answer_need: bool,
    planner_question_policy: str,
    planner_practice_policy: str,
    has_unsolicited_practice: bool,
    application_request: bool,
    practice_overview_requested: bool,
    answer_fit: dict[str, Any],
) -> MvpPart1Result:
    if pragmatics_repair_dissatisfaction:
        target = (last_direct_question or user_message).strip()
        target_lower = target.lower()
        if answer_obligation == "repair_and_answer_last_question" and "нейросталкинг" in target_lower:
            return MvpPart1Result(
                outcome="repair_answer_last_question",
                updated_text=text,
                updated_lowered_text=lowered_text,
                computed_target=target,
            )
        return MvpPart1Result(
            outcome="repair_user_dissatisfaction",
            updated_text=text,
            updated_lowered_text=lowered_text,
            computed_target=target or user_message,
        )

    if pragmatics_contextual_followup and pragmatics_should_not_reconfirm:
        if "хочешь" in lowered_text and "?" in text:
            text = re.sub(r"\s*\?+\s*", ". ", text).strip()
            lowered_text = text.lower()
        if "сфокусируюсь на разборе" in lowered_text or "без практик по умолчанию" in lowered_text:
            if pragmatics_offer_type in {"short_phrase", "one_step", "practice_observation"}:
                return MvpPart1Result(
                    outcome="contextual_followup_short_phrase",
                    updated_text=text,
                    updated_lowered_text=lowered_text,
                )
            if pragmatics_offer_type in {"example", "application", "explanation"}:
                return MvpPart1Result(
                    outcome="contextual_followup_example",
                    updated_text=text,
                    updated_lowered_text=lowered_text,
                )
            return MvpPart1Result(
                outcome="contextual_followup_direct",
                updated_text=text,
                updated_lowered_text=lowered_text,
            )

    if planner_safety_priority or planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
        if has_question or len(text) > 380:
            return MvpPart1Result(
                outcome="safety_grounding_literal",
                updated_text=text,
                updated_lowered_text=lowered_text,
                return_text="Я рядом. Сейчас важнее немного стабилизироваться и снизить перегруз, без лишнего давления.",
            )
        return MvpPart1Result(
            outcome="safety_grounding_passthrough",
            updated_text=text,
            updated_lowered_text=lowered_text,
            return_text=text,
        )

    if canned_step_disallowed and (planner_answer_shape == "one_step" or planner_next_move == "give_direct_step"):
        return MvpPart1Result(
            outcome="sanitized_direct_no_forced_practice",
            updated_text=text,
            updated_lowered_text=lowered_text,
        )

    if planner_answer_shape == "one_step" or user_step_request:
        return MvpPart1Result(
            outcome="one_step",
            updated_text=text,
            updated_lowered_text=lowered_text,
        )

    if summary_request:
        return MvpPart1Result(
            outcome="structured_summary",
            updated_text=text,
            updated_lowered_text=lowered_text,
        )

    if sarcasm_or_negative_feedback:
        return MvpPart1Result(
            outcome="sarcasm_negative_feedback_repair",
            updated_text=text,
            updated_lowered_text=lowered_text,
        )

    if direct_concrete_request:
        return MvpPart1Result(
            outcome="direct_concrete_request_repair",
            updated_text=text,
            updated_lowered_text=lowered_text,
        )

    if explicit_answer_need and has_question and planner_question_policy in {"none", "optional_none"}:
        return MvpPart1Result(
            outcome="direct_no_forced_question",
            updated_text=text,
            updated_lowered_text=lowered_text,
            return_text=re.sub(r"\s*\?+\s*", ". ", text).strip(),
        )

    if planner_practice_policy == "forbidden" and has_unsolicited_practice and not user_step_request:
        stale_stub = detect_stale_stub(text)
        preserve_direct_answer = (
            answer_obligation
            in {
                "acknowledge_style_preference_then_answer",
                "answer_direct_question",
                "answer_knowledge_question",
                "provide_one_bounded_practice",
                "answer_last_offer",
                "repair_and_answer_last_question",
            }
            or application_request
            or practice_overview_requested
        )
        if preserve_direct_answer and not bool(stale_stub.get("detected", False)) and len(text.strip()) >= 220:
            sanitized_text = _strip_optional_followup_invitation(text)
            if sanitized_text:
                return MvpPart1Result(
                    outcome="practice_forbidden_sanitized",
                    updated_text=text,
                    updated_lowered_text=lowered_text,
                    return_text=sanitized_text,
                )
        if bool(answer_fit.get("needs_repair", False)) or bool(answer_fit.get("concrete_need", False)) or application_request:
            return MvpPart1Result(
                outcome="practice_forbidden_repair_needed",
                updated_text=text,
                updated_lowered_text=lowered_text,
                return_text=_strip_optional_followup_invitation(text) or text,
                last_debug_patch={"answer_fit_repair_applied": True, "template_leakage_repair_deferred_to_gate": True},
            )
        return MvpPart1Result(
            outcome="practice_forbidden_repair_default",
            updated_text=text,
            updated_lowered_text=lowered_text,
            return_text=_strip_optional_followup_invitation(text) or text,
            last_debug_patch={"answer_fit_repair_applied": True, "template_leakage_repair_deferred_to_gate": True},
        )

    return MvpPart1Result(outcome="not_matched", updated_text=text, updated_lowered_text=lowered_text)
