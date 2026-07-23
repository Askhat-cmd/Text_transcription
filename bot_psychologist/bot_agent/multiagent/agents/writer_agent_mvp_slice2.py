from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .writer_agent_fallback_helpers import _strip_optional_followup_invitation
from ..stale_stub_detector import detect_stale_stub


MvpPart2Outcome = Literal[
    "not_matched",
    "practice_catalog_repair",
    "direct_no_forced_question",
    "repair_and_expand",
    "concept_explanation_repair",
    "preserved_application_answer",
    "concept_expansion_repair",
    "expanded_explanation_repair",
    "stale_stub_retry_deferred_to_gate",
]


@dataclass(frozen=True)
class MvpPart2Result:
    outcome: MvpPart2Outcome
    return_text: Optional[str] = None
    last_debug_patch: dict[str, Any] = field(default_factory=dict)


_ANSWER_OBLIGATIONS_PRESERVE = {
    "answer_direct_question",
    "answer_knowledge_question",
    "provide_one_bounded_practice",
    "answer_last_offer",
    "repair_and_answer_last_question",
}


def _classify_mvp_part2(
    *,
    text: str,
    user_message: str,
    lowered_user: str,
    concept: str,
    practice_overview_requested: bool,
    planner_answer_shape: str,
    planner_question_policy: str,
    has_question: bool,
    expansion_requested: bool,
    repair_and_expand_requested: bool,
    user_repair_signal: bool,
    should_answer_directly: bool,
    asks_define_known_term: bool,
    has_external_surveillance_frame: bool,
    application_request: bool,
    active_line_intent: str,
    answer_obligation: str,
    answer_fit: dict[str, Any],
) -> MvpPart2Result:
    if practice_overview_requested or planner_answer_shape == "practice_catalog_explanation":
        list_items = re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text)
        if len(list_items) < 3 or len(text) < 420:
            return MvpPart2Result(outcome="practice_catalog_repair")

    if planner_question_policy == "none" and has_question and not expansion_requested:
        return MvpPart2Result(
            outcome="direct_no_forced_question",
            return_text=re.sub(r"\s*\?+\s*", ". ", text).strip(),
        )

    if repair_and_expand_requested or user_repair_signal:
        return MvpPart2Result(outcome="repair_and_expand")

    if should_answer_directly and (asks_define_known_term or has_external_surveillance_frame):
        return MvpPart2Result(outcome="concept_explanation_repair")

    if (expansion_requested or application_request) and len(text) < 260:
        if answer_obligation in _ANSWER_OBLIGATIONS_PRESERVE:
            preserved_text = _strip_optional_followup_invitation(text)
            preserved_lower = preserved_text.lower()
            if (
                len(preserved_text) >= 120
                or any(color in preserved_lower for color in ("красн", "оранж", "зелен"))
                or "нейросталкинг" in preserved_lower
            ):
                return MvpPart2Result(
                    outcome="preserved_application_answer",
                    return_text=preserved_text,
                )
        if concept == "нейросталкинг" or "нейросталкинг" in lowered_user or active_line_intent == "known_concept_question":
            return MvpPart2Result(outcome="concept_expansion_repair")
        return MvpPart2Result(outcome="expanded_explanation_repair")

    stale_stub = detect_stale_stub(text)
    if bool(stale_stub.get("detected", False)):
        return MvpPart2Result(
            outcome="stale_stub_retry_deferred_to_gate",
            return_text=text,
            last_debug_patch={
                "answer_fit_repair_applied": bool(answer_fit.get("concrete_need", False)),
                "template_leakage_repair_deferred_to_gate": True,
            },
        )

    sanitized_final = text
    if answer_obligation in _ANSWER_OBLIGATIONS_PRESERVE:
        sanitized_final = _strip_optional_followup_invitation(text) or text
    return MvpPart2Result(outcome="not_matched", return_text=sanitized_final)
