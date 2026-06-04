"""Writer-first final answer directive builder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .dialogue_policy import DIALOGUE_PROFILE_MVP_FREE, normalize_dialogue_profile

FINAL_ANSWER_DIRECTIVE_VERSION = "final_answer_directive_v1"
FINAL_DIRECTIVE_AUTHORITY_ORDER = [
    "minimal_safety_baseline",
    "explicit_user_request",
    "repair_or_dissatisfaction",
    "accepted_previous_offer",
    "knowledge_or_concept_need",
    "conversation_continuity",
    "writer_freedom",
    "planner_and_diagnostic_advisory",
]

_REPAIR_MARKERS = (
    "ты не ответил",
    "это не ответ",
    "почему ты не продолжил",
    "заглючило",
    "не понял",
    "объясни нормально",
)
_THANKS_MARKERS = ("спасибо", "благодарю", "thanks", "thank you")


@dataclass
class FinalAnswerDirective:
    version: str
    profile: str
    user_intent: str
    answer_obligation: str
    must_answer: str
    answer_shape: str
    depth: str
    style: str
    question_policy: str
    practice_policy: str
    rag_policy: str
    diagnostic_center_role: str
    planner_role: str
    active_line_role: str
    diagnostic_card_role: str
    writer_autonomy: str
    hard_boundaries: list[str]
    advisory_context: dict[str, Any]
    suppressed_legacy_constraints: list[str]
    source_signals: dict[str, Any]
    conflict_resolution: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile": self.profile,
            "user_intent": self.user_intent,
            "answer_obligation": self.answer_obligation,
            "must_answer": self.must_answer,
            "answer_shape": self.answer_shape,
            "depth": self.depth,
            "style": self.style,
            "question_policy": self.question_policy,
            "practice_policy": self.practice_policy,
            "rag_policy": self.rag_policy,
            "diagnostic_center_role": self.diagnostic_center_role,
            "planner_role": self.planner_role,
            "active_line_role": self.active_line_role,
            "diagnostic_card_role": self.diagnostic_card_role,
            "writer_autonomy": self.writer_autonomy,
            "hard_boundaries": list(self.hard_boundaries),
            "advisory_context": dict(self.advisory_context),
            "suppressed_legacy_constraints": list(self.suppressed_legacy_constraints),
            "source_signals": dict(self.source_signals),
            "conflict_resolution": dict(self.conflict_resolution),
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _is_yes_followup(text: str) -> bool:
    return _normalize(text) in {"да", "ага", "ок", "окей", "yes", "yep", "да, конечно", "давай"}


def _is_close_ack(text: str) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in _THANKS_MARKERS) and len(lowered) <= 30


def _is_repair_message(text: str, *, pragmatics: dict[str, Any], dialogue_policy: dict[str, Any]) -> bool:
    if bool(pragmatics.get("repair_user_dissatisfaction", False)):
        return True
    if bool(dialogue_policy.get("sarcasm_or_negative_feedback", False)):
        return True
    lowered = _normalize(text)
    return any(marker in lowered for marker in _REPAIR_MARKERS)


def _is_comparison_request(text: str) -> bool:
    lowered = _normalize(text)
    return ("чем отличается" in lowered and " от " in lowered) or (
        "difference between" in lowered and " and " in lowered
    )


def _derive_obligation(
    *,
    user_message: str,
    dialogue_policy: dict[str, Any],
    dialogue_pragmatics: dict[str, Any],
    knowledge_answer_guard: dict[str, Any],
) -> tuple[str, str, str, str, str, str]:
    lowered = _normalize(user_message)
    fresh_chat_policy = (
        dict(dialogue_policy.get("fresh_chat_context_policy", {}))
        if isinstance(dialogue_policy.get("fresh_chat_context_policy"), dict)
        else {}
    )
    knowledge_answer = (
        dict(knowledge_answer_guard.get("knowledge_answer", {}))
        if isinstance(knowledge_answer_guard.get("knowledge_answer"), dict)
        else {}
    )
    fresh_simple_contact = bool(
        fresh_chat_policy.get("is_greeting_or_contact", False)
        and not bool(knowledge_answer.get("needed", False))
        and not bool(dialogue_policy.get("explicit_answer_need", False))
    )
    if fresh_simple_contact:
        return (
            "fresh_contact",
            "respond_to_contact",
            "simple_contact",
            "short",
            "optional_none",
            "none",
        )
    if _is_close_ack(user_message):
        return (
            "close_ack",
            "close_gently",
            "close_with_short_ack",
            "very_short",
            "none",
            "none",
        )
    if _is_repair_message(user_message, pragmatics=dialogue_pragmatics, dialogue_policy=dialogue_policy):
        return (
            "repair_after_failed_answer",
            "answer_previous_question_directly",
            "brief_apology_then_direct_answer",
            "short",
            "do_not_ask_until_answered",
            "none",
        )
    if bool(dialogue_pragmatics.get("is_contextual_followup", False)) and bool(
        dialogue_pragmatics.get("should_not_ask_confirmation_again", False)
    ) and _is_yes_followup(user_message):
        offer_type = str(dialogue_pragmatics.get("previous_assistant_offer_type", "unknown") or "unknown")
        return (
            "accepted_previous_offer",
            "fulfill_previous_offer",
            f"fulfill_offer:{offer_type}",
            "medium",
            "do_not_ask",
            "optional_if_relevant",
        )
    if _is_comparison_request(user_message):
        return (
            "concept_comparison",
            "compare_two_concepts_directly",
            user_message.strip(),
            "medium",
            "optional_none",
            "optional_if_relevant",
        )
    if bool(dialogue_policy.get("practice_overview_requested", False)):
        return (
            "practice_overview",
            "provide_multi_direction_practice_overview",
            user_message.strip(),
            "medium",
            "optional_none",
            "optional_if_relevant",
        )
    if bool(dialogue_policy.get("explicit_answer_need", False)) or "?" in lowered:
        return (
            "direct_answer_need",
            "answer_user_question_directly",
            user_message.strip(),
            "medium",
            "optional_none",
            "optional_if_relevant",
        )
    return (
        "continuity",
        "continue_line_with_focus",
        user_message.strip(),
        "medium",
        "optional_none",
        "optional_if_relevant",
    )


def _suppressed_constraints(*, profile: str, safety_active: bool) -> list[str]:
    if profile != DIALOGUE_PROFILE_MVP_FREE or safety_active:
        return []
    return [
        "writer_move.max_sentences=5",
        "writer_move.max_questions=1",
        "writer_move.must_do.ask_one_specific_question",
        "diagnostic_card.ask_at_most_one_question",
        "response_planner.response_depth=short",
        "active_line.should_ask_question=true",
        "active_line.practice_suppression_active=true",
    ]


def build_final_answer_directive_v1(
    *,
    user_message: str,
    dialogue_policy: dict[str, Any] | None,
    dialogue_pragmatics: dict[str, Any] | None,
    response_planner: dict[str, Any] | None,
    active_line: dict[str, Any] | None,
    diagnostic_card: dict[str, Any] | None,
    diagnostic_center_shadow: dict[str, Any] | None,
    retrieval_decision: dict[str, Any] | None,
    knowledge_answer_guard: dict[str, Any] | None,
    thread_state: Any,
    state_snapshot: Any,
) -> FinalAnswerDirective:
    policy = dict(dialogue_policy or {})
    pragmatics = dict(dialogue_pragmatics or {})
    planner = dict(response_planner or {})
    line = dict(active_line or {})
    card = dict(diagnostic_card or {})
    shadow = dict(diagnostic_center_shadow or {})
    retrieval = dict(retrieval_decision or {})
    knowledge = dict(knowledge_answer_guard or {})
    profile = normalize_dialogue_profile(policy.get("profile", "safe_guided"))
    safety_active = bool(getattr(state_snapshot, "safety_flag", False)) or bool(
        getattr(thread_state, "safety_active", False)
    )

    user_intent, answer_obligation, must_answer, depth, question_policy, rag_policy = _derive_obligation(
        user_message=user_message,
        dialogue_policy=policy,
        dialogue_pragmatics=pragmatics,
        knowledge_answer_guard=knowledge,
    )
    if user_intent == "fresh_contact":
        answer_shape = "simple_contact"
    elif user_intent == "repair_after_failed_answer":
        answer_shape = "repair_acknowledgement"
    elif user_intent == "concept_comparison":
        answer_shape = "definition_then_difference_then_example"
    else:
        answer_shape = str(planner.get("answer_shape", "compact_direct") or "compact_direct")
    style = "human_conversational"
    if user_intent == "repair_after_failed_answer":
        style = "brief_apology_then_direct_answer"
    elif user_intent == "close_ack":
        style = "short_warm_close"

    advisory_only = profile == DIALOGUE_PROFILE_MVP_FREE and not safety_active
    writer_autonomy = str(policy.get("writer_autonomy", "guided") or "guided")
    if advisory_only and writer_autonomy != "guarded_safety":
        writer_autonomy = "high"

    source_signals = {
        "dialogue_policy": policy,
        "dialogue_pragmatics": pragmatics,
        "response_planner": planner,
        "active_line": line,
        "diagnostic_card_summary": {
            "situation_label": str(card.get("situation_label", "") or ""),
            "suggested_writer_move": str(card.get("suggested_writer_move", "") or ""),
            "current_need": str(card.get("current_need", "") or ""),
            "confidence": float(card.get("confidence", 0.0) or 0.0),
        },
        "diagnostic_center_shadow": shadow,
        "retrieval_decision": retrieval,
        "knowledge_answer_guard": knowledge,
    }

    advisory_context = {
        "planner_suggestion": str(planner.get("next_move", "") or ""),
        "active_line_intent": str(line.get("user_intent", "unknown") or "unknown"),
        "diagnostic_need": str(card.get("current_need", "") or ""),
        "diagnostic_suggested_move": str(card.get("suggested_writer_move", "") or ""),
    }

    return FinalAnswerDirective(
        version=FINAL_ANSWER_DIRECTIVE_VERSION,
        profile=profile,
        user_intent=user_intent,
        answer_obligation=answer_obligation,
        must_answer=must_answer,
        answer_shape=answer_shape,
        depth=depth,
        style=style,
        question_policy=question_policy,
        practice_policy=(
            "safety_first"
            if safety_active
            else str(planner.get("practice_policy", "forbidden") or "forbidden")
        ),
        rag_policy=rag_policy,
        diagnostic_center_role="advisory_context_only" if advisory_only else "guided_legacy",
        planner_role="advisory_context_only" if advisory_only else "guided_legacy",
        active_line_role="advisory_context_only" if advisory_only else "guided_legacy",
        diagnostic_card_role="advisory_context_only" if advisory_only else "guided_legacy",
        writer_autonomy=writer_autonomy,
        hard_boundaries=[
            "minimal_safety",
            "privacy",
            "no_diagnosis",
            "no_medical_legal_financial_directives",
        ],
        advisory_context=advisory_context,
        suppressed_legacy_constraints=_suppressed_constraints(profile=profile, safety_active=safety_active),
        source_signals=source_signals,
        conflict_resolution={
            "authority_order": list(FINAL_DIRECTIVE_AUTHORITY_ORDER),
            "safety_active": safety_active,
            "advisory_mode": advisory_only,
        },
    )


__all__ = [
    "FINAL_ANSWER_DIRECTIVE_VERSION",
    "FINAL_DIRECTIVE_AUTHORITY_ORDER",
    "FinalAnswerDirective",
    "build_final_answer_directive_v1",
]
