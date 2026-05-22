"""Deterministic Diagnostic Center v1 for Writer orientation."""

from __future__ import annotations

from typing import Any

from .creator_live_behavior_guard import (
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    collect_recent_turn_texts_v1,
    evaluate_anti_regulate_loop_v1,
)
from .contracts.context_package import ContextAssemblyPackage
from .contracts.diagnostic_card import (
    DiagnosticCard,
    DiagnosticCardTrace,
    DiagnosticEvidenceRef,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState


DIAGNOSTIC_CARD_VERSION = "diagnostic_card_v1"
DIAGNOSTIC_CARD_BUILDER = "deterministic_rules_v1"


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _get_relation_reason(thread_diagnostics: dict[str, Any] | None) -> str:
    if not isinstance(thread_diagnostics, dict):
        return ""
    relation = thread_diagnostics.get("relation")
    if not isinstance(relation, dict):
        return ""
    return _safe_text(relation.get("relation_reason"))


def _context_counts(context_package: ContextAssemblyPackage | None) -> tuple[int, int]:
    if context_package is None:
        return 0, 0
    return (
        len(getattr(context_package, "recent_turns_full", []) or []),
        len(getattr(context_package, "recent_turns_summarized", []) or []),
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = _safe_text(item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _resolve_current_need(thread_state: ThreadState) -> str:
    active_frame = thread_state.active_frame if isinstance(thread_state.active_frame, dict) else {}
    current_need = _safe_text(active_frame.get("current_need"))
    if current_need:
        return current_need
    fallback_by_mode = {
        "safe_override": "stabilize and prioritize safety",
        "regulate": "reduce overload and stabilize",
        "practice": "one realistic next step",
        "validate": "brief support without pressure",
        "reflect": "clarify one key point gently",
        "explore": "explore perspective carefully",
    }
    return fallback_by_mode.get(thread_state.response_mode, "safe supportive response")


def _resolve_situation_label(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    relation_reason: str,
) -> tuple[str, list[str]]:
    rules: list[str] = []
    if state_snapshot.safety_flag or thread_state.safety_active:
        rules.append("safety_override_rule")
        return "safety_override", rules

    if (
        state_snapshot.nervous_state in {"hypo", "hyper"}
        and state_snapshot.intent == "contact"
    ):
        rules.append("low_resource_contact_rule")
        return "low_resource_contact", rules

    if thread_state.response_mode == "practice" or state_snapshot.intent == "solution":
        rules.append("concrete_next_step_rule")
        return "concrete_next_step", rules

    if (
        thread_state.relation_to_thread == "continue"
        and relation_reason == "active_frame_semantic_continuity"
    ):
        rules.append("semantic_continuation_rule")
        return "semantic_continuation", rules

    if thread_state.relation_to_thread == "continue":
        rules.append("thread_continuation_rule")
        return "thread_continuation", rules

    if thread_state.relation_to_thread == "new_thread":
        rules.append("new_exploration_rule")
        return "new_exploration", rules

    rules.append("generic_support_rule")
    return "generic_support", rules


def _resolve_writer_move(
    *,
    user_message: str,
    context_package: ContextAssemblyPackage | None,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    relation_reason: str,
) -> tuple[str, list[str], dict[str, Any]]:
    rules: list[str] = []
    guard_payload: dict[str, Any] = {
        "version": "anti_regulate_loop_v1",
        "request_type": "unknown",
        "practice_or_regulate_should_be_suppressed": False,
        "reasons": [],
    }
    if state_snapshot.safety_flag or thread_state.safety_active:
        rules.append("move_safe_override")
        return "safe_override", rules, guard_payload

    recent_turn_texts = collect_recent_turn_texts_v1(
        list(getattr(context_package, "recent_turns_full", []) or []),
        last_n=3,
        assistant_only=True,
    )
    guard_payload = evaluate_anti_regulate_loop_v1(
        user_message=user_message,
        recent_turn_texts=recent_turn_texts,
        safety_active=bool(state_snapshot.safety_flag or thread_state.safety_active),
        response_mode=str(thread_state.response_mode or ""),
        suggested_writer_move="regulate_first"
        if state_snapshot.nervous_state in {"hypo", "hyper"}
        else str(thread_state.response_mode or ""),
    )
    request_type = str(guard_payload.get("request_type") or "")
    suppress = bool(guard_payload.get("practice_or_regulate_should_be_suppressed", False))
    if suppress:
        rules.append("anti_regulate_loop_v1_suppress")
        if request_type == REQUEST_TYPE_EXAMPLE:
            rules.append("move_give_concrete_example")
            return "give_concrete_example", rules, guard_payload
        if request_type == REQUEST_TYPE_EXPLAIN:
            rules.append("move_clarify_one_point")
            return "clarify_one_point", rules, guard_payload
        rules.append("move_validate_briefly")
        return "validate_briefly", rules, guard_payload

    if state_snapshot.nervous_state in {"hypo", "hyper"}:
        rules.append("move_regulate_first")
        return "regulate_first", rules, guard_payload

    if thread_state.response_mode == "practice":
        rules.append("move_offer_one_micro_step")
        return "offer_one_micro_step", rules, guard_payload

    if relation_reason == "active_frame_semantic_continuity":
        rules.append("move_reflect_pattern_once")
        return "reflect_pattern_once", rules, guard_payload

    if thread_state.response_mode == "reflect":
        rules.append("move_clarify_one_point")
        return "clarify_one_point", rules, guard_payload

    if thread_state.response_mode == "explore":
        rules.append("move_explore_carefully")
        return "explore_carefully", rules, guard_payload

    rules.append("move_validate_briefly")
    return "validate_briefly", rules, guard_payload


def _build_avoid_list(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    relation_reason: str,
) -> tuple[list[str], list[str]]:
    rules: list[str] = []
    avoid = [
        "do_not_give_directive_life_advice",
        "do_not_diagnose",
        "do_not_over_explain",
        "ask_at_most_one_question",
    ]
    avoid.extend(list(thread_state.must_avoid or []))
    rules.append("base_avoid_rules")

    if state_snapshot.nervous_state in {"hypo", "hyper"}:
        avoid.extend(
            [
                "avoid_deep_analysis",
                "avoid_long_explanations",
                "avoid_multiple_steps",
            ]
        )
        rules.append("low_resource_avoid_rules")

    if thread_state.response_mode == "practice" or state_snapshot.intent == "solution":
        avoid.extend(["avoid_abstract_theory", "offer_only_one_next_step"])
        rules.append("solution_avoid_rules")

    if relation_reason == "active_frame_semantic_continuity":
        avoid.extend(
            [
                "avoid_restarting_context",
                "avoid_generic_advice",
                "name_the_repetition_gently",
            ]
        )
        rules.append("semantic_continuity_avoid_rules")

    if state_snapshot.safety_flag or thread_state.safety_active:
        avoid.extend(["avoid_exploration", "prioritize_safety_protocol"])
        rules.append("safety_avoid_rules")

    return _dedupe(avoid), rules


def _build_risk_flags(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    relation_reason: str,
    context_package: ContextAssemblyPackage | None,
    thread_diagnostics: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    rules: list[str] = []

    if state_snapshot.nervous_state in {"hypo", "hyper"}:
        flags.append("low_resource")
        rules.append("risk_low_resource")

    if state_snapshot.safety_flag or thread_state.safety_active:
        flags.append("safety_active")
        rules.append("risk_safety_active")

    if relation_reason == "active_frame_semantic_continuity" and float(thread_state.continuity_score) < 0.25:
        flags.append("continuity_low_confidence")
        rules.append("risk_continuity_low_confidence")

    relation_diag = thread_diagnostics.get("relation") if isinstance(thread_diagnostics, dict) else {}
    if (
        isinstance(relation_diag, dict)
        and thread_state.relation_to_thread == "new_thread"
        and (
            bool(relation_diag.get("followup_marker_hit"))
            or bool(relation_diag.get("low_resource_continue_marker_hit"))
            or bool(relation_diag.get("active_frame_semantic_continue_hit"))
        )
    ):
        flags.append("new_thread_after_continuation_cue")
        rules.append("risk_new_thread_after_continuation_cue")

    recent_full_count, summarized_count = _context_counts(context_package)
    if recent_full_count + summarized_count <= 1:
        flags.append("context_sparse")
        rules.append("risk_context_sparse")

    if state_snapshot.intent == "explore" and thread_state.response_mode in {"validate", "regulate"}:
        flags.append("avoid_over_exploration")
        rules.append("risk_avoid_over_exploration")

    if thread_state.response_mode == "practice":
        flags.append("avoid_directive_advice")
        rules.append("risk_avoid_directive_advice")

    return _dedupe(flags), rules


def _build_confidence(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    relation_reason: str,
    context_package: ContextAssemblyPackage | None,
) -> tuple[float, str]:
    recent_full_count, summarized_count = _context_counts(context_package)
    context_available = (recent_full_count + summarized_count) > 0
    state_conf = float(state_snapshot.confidence)
    continuity = float(thread_state.continuity_score)

    high_signal = (
        context_available
        and continuity >= 0.25
        and (
            relation_reason in {"active_frame_semantic_continuity", "low_resource_continuation_marker"}
            or thread_state.response_mode in {"practice", "validate", "safe_override"}
        )
    )
    if high_signal:
        return 0.88, "confidence_high_coherent_signals"

    medium_signal = context_available and state_conf >= 0.6 and continuity >= 0.12
    if medium_signal:
        return 0.67, "confidence_medium_mixed_signals"

    return 0.45, "confidence_low_fallback"


def _build_user_state_summary(state_snapshot: StateSnapshot) -> str:
    return (
        f"{state_snapshot.nervous_state}/{state_snapshot.intent}: "
        f"openness={state_snapshot.openness}, ok_position={state_snapshot.ok_position}"
    )


def _build_thread_line_summary(*, thread_state: ThreadState, relation_reason: str) -> str:
    relation = thread_state.relation_to_thread
    if relation == "new_thread":
        return "new thread started"
    if relation == "continue" and relation_reason == "active_frame_semantic_continuity":
        return "semantic continuity preserved by active_frame guard"
    if relation == "continue" and relation_reason == "low_resource_continuation_marker":
        return "low-resource continuation preserved"
    if relation == "continue":
        return "continuing active thread"
    return f"{relation} thread transition"


def _build_evidence_refs(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    context_package: ContextAssemblyPackage | None,
    relation_reason: str,
) -> list[DiagnosticEvidenceRef]:
    recent_full_count, summarized_count = _context_counts(context_package)
    evidence = [
        DiagnosticEvidenceRef("state", "nervous_state", state_snapshot.nervous_state),
        DiagnosticEvidenceRef("state", "intent", state_snapshot.intent),
        DiagnosticEvidenceRef("state", "openness", state_snapshot.openness),
        DiagnosticEvidenceRef("thread", "relation_to_thread", thread_state.relation_to_thread),
        DiagnosticEvidenceRef("thread", "relation_reason", relation_reason or "unknown"),
        DiagnosticEvidenceRef("thread", "response_mode", thread_state.response_mode),
        DiagnosticEvidenceRef(
            "thread",
            "pattern_core_present",
            "true" if bool(_safe_text(thread_state.pattern_core)) else "false",
        ),
        DiagnosticEvidenceRef("context", "recent_full_count", str(recent_full_count)),
        DiagnosticEvidenceRef("context", "summarized_count", str(summarized_count)),
    ]
    return evidence


def build_diagnostic_card_v1(
    *,
    user_message: str = "",
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    context_package: ContextAssemblyPackage | None,
    thread_diagnostics: dict[str, Any] | None = None,
) -> DiagnosticCard:
    """Build deterministic v1 card from existing pipeline signals."""
    relation_reason = _get_relation_reason(thread_diagnostics)
    situation_label, situation_rules = _resolve_situation_label(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        relation_reason=relation_reason,
    )
    suggested_writer_move, move_rules, behavior_guard = _resolve_writer_move(
        user_message=user_message,
        context_package=context_package,
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        relation_reason=relation_reason,
    )
    avoid_list, avoid_rules = _build_avoid_list(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        relation_reason=relation_reason,
    )
    risk_flags, risk_rules = _build_risk_flags(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        relation_reason=relation_reason,
        context_package=context_package,
        thread_diagnostics=thread_diagnostics,
    )
    confidence, confidence_rule = _build_confidence(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        relation_reason=relation_reason,
        context_package=context_package,
    )
    evidence_refs = _build_evidence_refs(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        context_package=context_package,
        relation_reason=relation_reason,
    )
    request_type = str(behavior_guard.get("request_type", "unknown") or "unknown")
    practice_suppressed = bool(
        behavior_guard.get("practice_or_regulate_should_be_suppressed", False)
    )
    suppression_reasons = [
        str(item)
        for item in list(behavior_guard.get("reasons", []) or [])
        if str(item).strip()
    ]
    evidence_refs.extend(
        [
            DiagnosticEvidenceRef("behavior_guard", "request_type", request_type),
            DiagnosticEvidenceRef(
                "behavior_guard",
                "practice_suppressed",
                "true" if practice_suppressed else "false",
            ),
        ]
    )
    if suppression_reasons:
        evidence_refs.append(
            DiagnosticEvidenceRef(
                "behavior_guard",
                "practice_suppression_reasons",
                ",".join(suppression_reasons),
            )
        )

    trace = DiagnosticCardTrace(
        version=DIAGNOSTIC_CARD_VERSION,
        builder=DIAGNOSTIC_CARD_BUILDER,
        rules_applied=(
            situation_rules
            + move_rules
            + avoid_rules
            + risk_rules
            + [f"request_type={request_type}"]
            + [f"practice_suppressed={'true' if practice_suppressed else 'false'}"]
            + [f"practice_suppression_reason={item}" for item in suppression_reasons]
            + [confidence_rule]
        ),
        risk_flags=list(risk_flags),
        evidence_sources=_dedupe([item.source for item in evidence_refs]),
    )
    return DiagnosticCard(
        version=DIAGNOSTIC_CARD_VERSION,
        situation_label=situation_label,
        user_state_summary=_build_user_state_summary(state_snapshot),
        thread_line_summary=_build_thread_line_summary(
            thread_state=thread_state,
            relation_reason=relation_reason,
        ),
        current_need=_resolve_current_need(thread_state),
        suggested_writer_move=suggested_writer_move,
        avoid_list=avoid_list,
        evidence_refs=evidence_refs,
        confidence=confidence,
        risk_flags=risk_flags,
        trace=trace,
    )
