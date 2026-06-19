"""Writer-first final answer directive builder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .dialogue_policy import (
    DIALOGUE_PROFILE_MVP_FREE,
    normalize_dialogue_profile,
    resolve_profile_preset,
)

FINAL_ANSWER_DIRECTIVE_VERSION = "final_answer_directive_v1"
FINAL_DIRECTIVE_AUTHORITY_ORDER = [
    "minimal_safety_baseline",
    "explicit_user_request",
    "answer_obligation",
    "last_offer_or_unanswered_question_recovery",
    "style_preference",
    "knowledge_or_concept_need",
    "planner_and_diagnostic_advisory",
    "writer_freedom",
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
_CURRENT_TURN_MUST_ANSWER_PATTERNS = (
    re.compile(r"не\s+нужн\w*\s+практик\w*", re.IGNORECASE),
    re.compile(r"не\s+хоч\w*\s+практик\w*", re.IGNORECASE),
    re.compile(r"хоч\w*\s+понят\w*\s+причин\w*", re.IGNORECASE),
    re.compile(r"не\s+последств\w*", re.IGNORECASE),
    re.compile(r"почему\s+меня\s+так\s+злит", re.IGNORECASE),
    re.compile(r"что\s+с\s+причин\w*", re.IGNORECASE),
    re.compile(r"как\s+быть\s+с\s+причин\w*", re.IGNORECASE),
)


@dataclass
class FinalAnswerDirective:
    version: str
    profile: str
    profile_preset: str
    unified_dialogue_policy_version: str
    user_intent: str
    dialogue_act: str
    answer_obligation: str
    must_answer: str
    answer_shape: str
    depth: str
    style: str
    question_policy: str
    practice_policy: str
    summary_request: bool
    summary_scope: str
    no_confirmation_needed: bool
    no_practice_unless_requested: bool
    summary_context_anchors: list[str]
    rag_policy: str
    diagnostic_center_role: str
    planner_role: str
    active_line_role: str
    diagnostic_card_role: str
    writer_autonomy: str
    hard_boundaries: list[str]
    soft_guidance: list[str]
    style_state_summary: dict[str, Any]
    last_assistant_offer_summary: dict[str, Any]
    unanswered_question_summary: dict[str, Any]
    advisory_context: dict[str, Any]
    suppressed_legacy_constraints: list[str]
    source_signals: dict[str, Any]
    conflict_resolution: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile": self.profile,
            "profile_preset": self.profile_preset,
            "unified_dialogue_policy_version": self.unified_dialogue_policy_version,
            "user_intent": self.user_intent,
            "dialogue_act": self.dialogue_act,
            "answer_obligation": self.answer_obligation,
            "must_answer": self.must_answer,
            "answer_shape": self.answer_shape,
            "depth": self.depth,
            "style": self.style,
            "question_policy": self.question_policy,
            "practice_policy": self.practice_policy,
            "summary_request": bool(self.summary_request),
            "summary_scope": self.summary_scope,
            "no_confirmation_needed": bool(self.no_confirmation_needed),
            "no_practice_unless_requested": bool(self.no_practice_unless_requested),
            "summary_context_anchors": list(self.summary_context_anchors),
            "rag_policy": self.rag_policy,
            "diagnostic_center_role": self.diagnostic_center_role,
            "planner_role": self.planner_role,
            "active_line_role": self.active_line_role,
            "diagnostic_card_role": self.diagnostic_card_role,
            "writer_autonomy": self.writer_autonomy,
            "hard_boundaries": list(self.hard_boundaries),
            "soft_guidance": list(self.soft_guidance),
            "style_state_summary": dict(self.style_state_summary),
            "last_assistant_offer_summary": dict(self.last_assistant_offer_summary),
            "unanswered_question_summary": dict(self.unanswered_question_summary),
            "advisory_context": dict(self.advisory_context),
            "suppressed_legacy_constraints": list(self.suppressed_legacy_constraints),
            "source_signals": dict(self.source_signals),
            "conflict_resolution": dict(self.conflict_resolution),
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _is_yes_followup(text: str) -> bool:
    return _normalize(text) in {"да", "ага", "ок", "окей", "yes", "yep", "да, конечно", "давай", "можно"}


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


def _derive_obligation_fallback(
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
        return ("fresh_contact", "respond_to_contact", "simple_contact", "short", "optional_none", "none")
    if _is_close_ack(user_message):
        return ("close_ack", "close_gently", "close_with_short_ack", "very_short", "none", "none")
    if _is_repair_message(user_message, pragmatics=dialogue_pragmatics, dialogue_policy=dialogue_policy):
        return (
            "repair_after_failed_answer",
            "answer_previous_question_directly",
            "brief_apology_then_direct_answer",
            "short",
            "do_not_ask_until_answered",
            "none",
        )
    if bool(dialogue_pragmatics.get("is_contextual_followup", False)) and bool(dialogue_pragmatics.get("should_not_ask_confirmation_again", False)) and _is_yes_followup(user_message):
        offer_type = str(dialogue_pragmatics.get("previous_assistant_offer_type", "unknown") or "unknown")
        return ("accepted_previous_offer", "fulfill_previous_offer", f"fulfill_offer:{offer_type}", "medium", "do_not_ask", "optional_if_relevant")
    if _is_comparison_request(user_message):
        return ("concept_comparison", "compare_two_concepts_directly", user_message.strip(), "medium", "optional_none", "optional_if_relevant")
    if bool(dialogue_policy.get("practice_overview_requested", False)):
        return ("practice_overview", "provide_multi_direction_practice_overview", user_message.strip(), "medium", "optional_none", "optional_if_relevant")
    if bool(dialogue_policy.get("explicit_answer_need", False)) or "?" in lowered:
        return ("direct_answer_need", "answer_user_question_directly", user_message.strip(), "medium", "optional_none", "optional_if_relevant")
    return ("continuity", "continue_line_with_focus", user_message.strip(), "medium", "optional_none", "optional_if_relevant")


def _must_answer_current_turn(user_message: str) -> bool:
    text = str(user_message or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _CURRENT_TURN_MUST_ANSWER_PATTERNS)


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
    answer_obligation_resolution: dict[str, Any] | None = None,
    unified_dialogue_profile: dict[str, Any] | None = None,
) -> FinalAnswerDirective:
    policy = dict(dialogue_policy or {})
    pragmatics = dict(dialogue_pragmatics or {})
    planner = dict(response_planner or {})
    line = dict(active_line or {})
    card = dict(diagnostic_card or {})
    shadow = dict(diagnostic_center_shadow or {})
    retrieval = dict(retrieval_decision or {})
    knowledge = dict(knowledge_answer_guard or {})
    obligation_resolution = dict(answer_obligation_resolution or {})
    unified_policy = dict(unified_dialogue_profile or {})

    profile = normalize_dialogue_profile(policy.get("profile", "safe_guided"))
    profile_preset = str(policy.get("profile_preset") or resolve_profile_preset(profile))
    safety_active = bool(getattr(state_snapshot, "safety_flag", False)) or bool(getattr(thread_state, "safety_active", False))

    fallback_intent, fallback_obligation, fallback_style, fallback_depth, fallback_question_policy, fallback_rag_policy = _derive_obligation_fallback(
        user_message=user_message,
        dialogue_policy=policy,
        dialogue_pragmatics=pragmatics,
        knowledge_answer_guard=knowledge,
    )

    dialogue_act = str(
        obligation_resolution.get("dialogue_act")
        or dict(policy.get("dialogue_act_resolution", {})).get("dialogue_act", "unknown")
    )
    effective_user_intent = str(dialogue_act if dialogue_act and dialogue_act != "unknown" else fallback_intent)
    answer_obligation = str(obligation_resolution.get("answer_obligation", fallback_obligation) or fallback_obligation)
    answer_shape = str(obligation_resolution.get("answer_shape", planner.get("answer_shape", "compact_direct")) or planner.get("answer_shape", "compact_direct"))
    depth = str(obligation_resolution.get("depth", fallback_depth) or fallback_depth)
    question_policy = str(obligation_resolution.get("question_policy", planner.get("question_policy", fallback_question_policy)) or planner.get("question_policy", fallback_question_policy))
    style_overrides = dict(obligation_resolution.get("style_overrides", {})) if isinstance(obligation_resolution.get("style_overrides"), dict) else {}
    tone = str(style_overrides.get("tone", "neutral") or "neutral")
    complexity = str(style_overrides.get("complexity_preference", "normal") or "normal")
    style_bits = [tone]
    if style_overrides.get("avoid_overexplaining"):
        style_bits.append("brief")
    if complexity != "normal":
        style_bits.append(complexity)
    style = ", ".join(style_bits) if obligation_resolution else fallback_style
    practice_policy = str(
        obligation_resolution.get("practice_policy", planner.get("practice_policy", "forbidden"))
        or planner.get("practice_policy", "forbidden")
    )
    rag_policy = fallback_rag_policy
    if retrieval.get("retrieval_action") in {"include_relevant_rag", "knowledge_grounding", "contextual_grounding"}:
        rag_policy = "context_package_only"

    if answer_shape == "compact_direct" and answer_obligation in {"answer_knowledge_question", "acknowledge_style_preference_then_answer", "answer_last_offer", "continue_thread"}:
        answer_shape = "structured_explanation"
    if answer_obligation == "compare_two_concepts_directly":
        answer_shape = "definition_then_difference_then_example"
    if answer_obligation == "provide_one_bounded_practice":
        question_policy = "none"
        practice_policy = "allowed_explicit_request"

    style_state_summary = dict(policy.get("dialogue_style_state", {})) if isinstance(policy.get("dialogue_style_state"), dict) else {}
    last_offer_summary = dict(policy.get("last_assistant_offer", {})) if isinstance(policy.get("last_assistant_offer"), dict) else {}
    unanswered_summary = dict(policy.get("unanswered_question_state", {})) if isinstance(policy.get("unanswered_question_state"), dict) else {}
    summary_request = bool(
        answer_obligation == "summarize_current_conversation"
        or dialogue_act == "summary_request"
        or obligation_resolution.get("summary_request", False)
    )
    summary_scope = (
        str(obligation_resolution.get("summary_scope", "") or "")
        or str(dict(policy.get("dialogue_act_resolution", {})).get("summary_scope", "") or "")
        or ("current_conversation" if summary_request else "")
    )
    no_confirmation_needed = bool(
        summary_request
        and (
            obligation_resolution.get("no_confirmation_needed", True)
            or obligation_resolution.get("should_not_confirm_last_offer", True)
        )
    )
    no_practice_unless_requested = bool(
        summary_request and obligation_resolution.get("no_practice_unless_requested", True)
    )
    summary_context_anchors: list[str] = []
    for value in (
        unanswered_summary.get("last_direct_user_question", ""),
        last_offer_summary.get("offer_text_summary", ""),
        user_message,
    ):
        anchor = str(value or "").strip()
        if anchor and anchor not in summary_context_anchors:
            summary_context_anchors.append(anchor[:180])
    if summary_request:
        answer_shape = "structured_summary"
        answer_obligation = "summarize_current_conversation"
        question_policy = "none"
        practice_policy = "forbidden"
        effective_user_intent = "summary_request"
        soft_guidance = [
            str(item)
            for item in list(policy.get("soft_guidance", unified_policy.get("soft_guidance", [])) or [])
            if str(item).strip()
        ]
        if "summarize_current_conversation_without_reconfirmation" not in soft_guidance:
            soft_guidance.append("summarize_current_conversation_without_reconfirmation")
    else:
        soft_guidance = [
            str(item)
            for item in list(policy.get("soft_guidance", unified_policy.get("soft_guidance", [])) or [])
            if str(item).strip()
        ]
    if summary_request:
        must_answer_value = "summary of current conversation"
    elif _must_answer_current_turn(user_message):
        must_answer_value = str(user_message or "").strip()
    else:
        must_answer_value = str(unanswered_summary.get("last_direct_user_question", "") or str(user_message or "").strip())

    return FinalAnswerDirective(
        version=FINAL_ANSWER_DIRECTIVE_VERSION,
        profile=profile,
        profile_preset=profile_preset,
        unified_dialogue_policy_version=str(unified_policy.get("version", policy.get("version", "unified_dialogue_policy_v2")) or "unified_dialogue_policy_v2"),
        user_intent=effective_user_intent,
        dialogue_act=str(dialogue_act or "unknown"),
        answer_obligation=answer_obligation,
        must_answer=must_answer_value,
        answer_shape=answer_shape,
        depth=depth,
        style=style,
        question_policy=question_policy,
        practice_policy=practice_policy,
        summary_request=summary_request,
        summary_scope=summary_scope,
        no_confirmation_needed=no_confirmation_needed,
        no_practice_unless_requested=no_practice_unless_requested,
        summary_context_anchors=summary_context_anchors if summary_request else [],
        rag_policy=rag_policy,
        diagnostic_center_role=str(policy.get("diagnostic_center_role", unified_policy.get("diagnostic_center_role", "advisory_context_only")) or "advisory_context_only"),
        planner_role=str(policy.get("planner_role", unified_policy.get("planner_role", "advisory_context_only")) or "advisory_context_only"),
        active_line_role=str(policy.get("active_line_role", unified_policy.get("active_line_role", "advisory_context_only")) or "advisory_context_only"),
        diagnostic_card_role=str(policy.get("diagnostic_card_role", unified_policy.get("diagnostic_card_role", "advisory_context_only")) or "advisory_context_only"),
        writer_autonomy=str(policy.get("writer_autonomy", unified_policy.get("effective_writer_autonomy", "medium")) or "medium"),
        hard_boundaries=[str(item) for item in list(policy.get("hard_boundaries", unified_policy.get("hard_boundaries", [])) or []) if str(item).strip()],
        soft_guidance=soft_guidance,
        style_state_summary=style_state_summary,
        last_assistant_offer_summary=last_offer_summary,
        unanswered_question_summary=unanswered_summary,
        advisory_context={
            "response_planner": planner,
            "active_line": line,
            "diagnostic_card": card,
            "diagnostic_center_shadow": shadow,
            "retrieval": retrieval,
            "knowledge_answer": knowledge.get("knowledge_answer", {}),
        },
        suppressed_legacy_constraints=_suppressed_constraints(profile=profile, safety_active=safety_active),
        source_signals={
            "dialogue_pragmatics": pragmatics,
            "dialogue_act_resolution": dict(policy.get("dialogue_act_resolution", {})) if isinstance(policy.get("dialogue_act_resolution"), dict) else {},
            "answer_obligation_resolution": obligation_resolution,
            "style_state_summary": style_state_summary,
            "summary_request": summary_request,
            "summary_scope": summary_scope,
            "no_confirmation_needed": no_confirmation_needed,
            "no_practice_unless_requested": no_practice_unless_requested,
        },
        conflict_resolution={
            "authority_order": FINAL_DIRECTIVE_AUTHORITY_ORDER,
            "safety_active": safety_active,
            "advisory_mode": True,
        },
    )
