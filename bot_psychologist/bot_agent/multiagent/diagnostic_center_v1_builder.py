"""Deterministic Diagnostic Center v1 dry-run builder (internal map layer)."""

from __future__ import annotations

from typing import Any

from .contracts.diagnostic_center_v1 import (
    DiagnosticCenterInput,
    DiagnosticCenterOutput,
    DiagnosticCenterTrace,
    DiagnosticHypothesis,
    DiagnosticLensSignal,
    NextMicroShift,
)


def _contains_any(text: str, parts: list[str]) -> bool:
    lowered = text.lower()
    return any(part in lowered for part in parts)


def _normalize_input(payload: DiagnosticCenterInput | dict[str, Any]) -> DiagnosticCenterInput:
    if isinstance(payload, DiagnosticCenterInput):
        return payload
    return DiagnosticCenterInput.from_dict(payload)


def _extract_lens_signals(knowledge_hits: list[dict[str, Any]]) -> list[DiagnosticLensSignal]:
    lens_scores: dict[str, float] = {}
    for item in knowledge_hits:
        if not isinstance(item, dict):
            continue
        lens = str(item.get("lens_family") or "").strip() or "unknown"
        score = float(item.get("score", 0.0) or 0.0)
        if score <= 0.0:
            continue
        prev = lens_scores.get(lens, 0.0)
        if score > prev:
            lens_scores[lens] = score
    signals = [
        DiagnosticLensSignal(
            lens_family=lens,
            score=score,
            source="knowledge_hits",
            rationale="retrieval metadata hint",
        )
        for lens, score in sorted(lens_scores.items(), key=lambda row: row[1], reverse=True)[:3]
    ]
    return signals


def _pick_next_shift(data: DiagnosticCenterInput, safety_first: bool) -> NextMicroShift:
    must_not = [
        "give_final_advice",
        "quote_kb_directly",
        "introduce_new_framework",
    ]
    must_do = ["validate_feeling"]

    if safety_first:
        return NextMicroShift(
            response_goal="safety_redirect",
            response_mode="ground_then_one_step",
            target_micro_shift="reduce activation and keep user safe",
            must_do=["grounding", "short_sentence", "one_step_only"],
            must_not_do=must_not + ["deep_analysis", "multiple_questions"],
            depth_allowed="none",
            max_questions=0,
            max_concepts=1,
        )

    if data.ok_position == "I-W+" and data.openness == "defensive":
        return NextMicroShift(
            response_goal="stabilize_authorship",
            response_mode="reflect_then_one_question",
            target_micro_shift="return authorship without pressure",
            must_do=must_do + ["name_one_mechanism_softly"],
            must_not_do=must_not + ["give_directive_certainty"],
            depth_allowed="low_to_medium",
            max_questions=1,
            max_concepts=1,
        )

    if data.ok_position == "I+W-" and data.openness == "defensive":
        return NextMicroShift(
            response_goal="decenter_without_shaming",
            response_mode="validate_then_reframe_softly",
            target_micro_shift="reduce accusation frame and restore dialogue",
            must_do=must_do + ["validate_feeling_without_confirming_frame"],
            must_not_do=must_not + ["join_accusation"],
            depth_allowed="low_to_medium",
            max_questions=1,
            max_concepts=1,
        )

    if data.ok_position == "I-W-" and data.openness == "collapsed":
        return NextMicroShift(
            response_goal="ground_and_reduce_load",
            response_mode="minimal_support",
            target_micro_shift="keep contact with minimal load",
            must_do=["grounding", "tiny_step"],
            must_not_do=must_not + ["deep_analysis"],
            depth_allowed="none",
            max_questions=0,
            max_concepts=1,
        )

    if data.intent in {"directive", "practical_step"}:
        return NextMicroShift(
            response_goal="clarify_before_action",
            response_mode="one_clarifying_question",
            target_micro_shift="avoid false certainty and keep guidance bounded",
            must_do=must_do + ["clarify_goal"],
            must_not_do=must_not + ["give_directive_certainty"],
            depth_allowed="low_to_medium",
            max_questions=1,
            max_concepts=1,
        )

    if data.ok_position == "I+W+" and data.openness == "open":
        return NextMicroShift(
            response_goal="deepen_and_integrate",
            response_mode="reflect_plus_alternative",
            target_micro_shift="expand perspective while preserving agency",
            must_do=must_do + ["offer_alternative_perspective"],
            must_not_do=must_not,
            depth_allowed="medium|high",
            max_questions=1,
            max_concepts=2,
        )

    return NextMicroShift(
        response_goal="clarify",
        response_mode="reflect_then_one_question",
        target_micro_shift="maintain thread and gently clarify current need",
        must_do=must_do,
        must_not_do=must_not,
        depth_allowed="low_to_medium",
        max_questions=1,
        max_concepts=1,
    )


def _build_hypothesis(data: DiagnosticCenterInput, safety_first: bool, lens_signals: list[DiagnosticLensSignal]) -> DiagnosticHypothesis:
    evidence = [
        f"nervous_state:{data.nervous_state}",
        f"intent:{data.intent}",
        f"openness:{data.openness}",
        f"ok_position:{data.ok_position}",
        f"relation_to_thread:{data.relation_to_thread}",
        f"phase:{data.phase}",
    ]
    if data.pattern_core:
        evidence.append(f"pattern_core:{data.pattern_core[:64]}")

    risk_flags: list[str] = []
    confidence = 0.62
    pattern = "working_map_unknown"
    mechanism = "insufficient stable signals; keep gentle clarification"
    blind_spot = "may seek certainty before naming current mechanism"

    if safety_first:
        confidence = 0.8
        pattern = "high_activation_or_crisis_guard"
        mechanism = "safety-sensitive state likely limits capacity for deep exploration"
        blind_spot = "depth may overwhelm before stabilization"
        risk_flags.append("safety_first")
    elif data.ok_position == "I-W+":
        pattern = "confirmation_seeking_under_uncertainty"
        mechanism = "user may seek external permission instead of internal authorship"
        blind_spot = "question format can hide need for permission"
    elif data.ok_position == "I+W-":
        pattern = "decentering_needed_under_externalization"
        mechanism = "framing may externalize agency to others"
        blind_spot = "accusation frame can block self-observation"
    elif data.ok_position == "I-W-":
        pattern = "collapsed_agency_low_resource"
        mechanism = "energy/resource appears reduced; exploration load must stay minimal"
        blind_spot = "deep analysis can amplify helplessness"
        risk_flags.append("low_resource")
        confidence = 0.74
    elif data.ok_position == "I+W+":
        pattern = "integration_ready_exploration"
        mechanism = "user appears able to tolerate perspective broadening"
        blind_spot = "premature advice may reduce reflective quality"

    if data.relation_to_thread == "branch":
        pattern = f"{pattern}_branch"
        evidence.append("branch_detected")
    if lens_signals:
        evidence.append(f"lens_hint:{lens_signals[0].lens_family}")

    return DiagnosticHypothesis(
        pattern_candidate=pattern,
        mechanism_summary=mechanism,
        blind_spot_candidate=blind_spot,
        confidence=confidence,
        evidence=evidence,
        counter_evidence=[],
        risk_flags=risk_flags,
    )


def build_diagnostic_center_output_v1(payload: DiagnosticCenterInput | dict[str, Any]) -> DiagnosticCenterOutput:
    """Build internal Diagnostic Center output from deterministic rules only."""
    data = _normalize_input(payload)
    lens_signals = _extract_lens_signals(data.knowledge_hits)

    crisis_markers = ["суиц", "убить себя", "хочу умер", "не хочу жить"]
    text_crisis = _contains_any(data.user_message, crisis_markers)
    safety_first = data.safety_flag or data.nervous_state in {"hyper", "hypo"} or data.intent == "crisis" or text_crisis
    status = "safety_first" if safety_first else "ok"

    next_shift = _pick_next_shift(data, safety_first=safety_first)
    hypothesis = _build_hypothesis(data, safety_first=safety_first, lens_signals=lens_signals)

    rules = ["deterministic_dry_run_v1", "internal_only_contract"]
    if safety_first:
        rules.append("safety_priority_rule")
    if data.relation_to_thread == "branch":
        rules.append("branch_continuity_rule")
    if lens_signals:
        rules.append("kb_lens_internal_rule")
    rules.append("must_not_quote_source_rule")

    trace = DiagnosticCenterTrace(
        version="diagnostic_center_trace_v1",
        builder="diagnostic_center_dry_run_v1",
        rules_applied=rules,
        safety_priority_applied=safety_first,
        evidence_sources=["state_snapshot", "thread_state", "context_package", "knowledge_hits"],
        kb_usage_mode="internal_lens_only",
        must_not_quote_source=True,
    )

    return DiagnosticCenterOutput(
        schema_version="diagnostic_center_output_v1",
        status=status,
        nervous_state=data.nervous_state,
        intent=data.intent,
        openness=data.openness,
        ok_position=data.ok_position,
        relation_to_thread=data.relation_to_thread,
        phase=data.phase,
        working_hypothesis=hypothesis,
        lens_signals=lens_signals,
        next_micro_shift=next_shift,
        trace=trace,
        diagnostic_center_runtime_enabled=False,
        user_facing_text_generated=False,
    )
