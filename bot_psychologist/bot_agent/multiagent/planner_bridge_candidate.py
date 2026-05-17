"""Planner Bridge candidate builder (shadow-only, eval-only)."""

from __future__ import annotations

from typing import Any

from .contracts.diagnostic_card import DiagnosticCard
from .contracts.diagnostic_center_v1 import DiagnosticCenterOutput
from .contracts.planner_bridge_v1 import (
    PlannerBridgeGuardrails,
    PlannerBridgeInput,
    PlannerBridgeOutput,
    PlannerBridgeTrace,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState


def _dedupe(items: list[str], *, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def _is_safety_context(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    output: DiagnosticCenterOutput,
) -> bool:
    if output.status == "safety_first":
        return True
    if state_snapshot.safety_flag or thread_state.safety_active:
        return True
    if state_snapshot.nervous_state in {"hyper", "hypo"}:
        return True
    return False


def build_planner_bridge_candidate_v1(
    *,
    diagnostic_center_output: DiagnosticCenterOutput,
    divergence: dict[str, Any],
    divergence_severity: str,
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> PlannerBridgeOutput:
    input_contract = PlannerBridgeInput(
        diagnostic_center_output=diagnostic_center_output.to_dict(),
        divergence=dict(divergence or {}),
        divergence_severity=str(divergence_severity or "compatible"),
        diagnostic_card=diagnostic_card.to_dict(),
        thread_state=thread_state.to_dict(),
        state_snapshot=state_snapshot.to_dict(),
    )
    output = diagnostic_center_output
    blocked_reasons: list[str] = []
    rules: list[str] = ["shadow_only_guardrail"]

    kb_boundary_ok = bool(input_contract.divergence.get("kb_boundary_ok", True))
    raw_kb_exposed = bool(input_contract.divergence.get("raw_kb_text_exposed", False))
    kb_usage_mode = str(output.trace.kb_usage_mode or "none")
    if kb_usage_mode == "disabled":
        kb_usage_mode = "none"
    if kb_usage_mode not in {"none", "internal_lens_only", "practice_candidate_only"}:
        kb_usage_mode = "none"
    if not kb_boundary_ok or raw_kb_exposed:
        blocked_reasons.append("kb_boundary_violation")
        rules.append("kb_boundary_block")

    hard_blockers = [str(item) for item in input_contract.divergence.get("hard_blocker_reasons", []) if str(item).strip()]
    if divergence_severity == "hard_blocker":
        blocked_reasons.extend(hard_blockers or ["hard_blocker"])
        rules.append("hard_blocker_gate")

    safety_context = _is_safety_context(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        output=output,
    )
    if safety_context:
        status = "limited"
        depth_limit = "low" if output.next_micro_shift.depth_allowed in {"low", "low_to_medium"} else "none"
        max_questions = 0
        max_concepts = 1
        safety_constraints = ["safety_first"]
        rules.append("safety_limited_mode")
    else:
        status = "candidate"
        depth_limit = output.next_micro_shift.depth_allowed
        if depth_limit not in {"none", "low", "low_to_medium", "medium", "high"}:
            depth_limit = "low_to_medium"
        max_questions = min(1, int(output.next_micro_shift.max_questions))
        max_concepts = min(2, int(output.next_micro_shift.max_concepts))
        safety_constraints = []

    if thread_state.ok_position == "I-W-" and thread_state.openness == "collapsed":
        status = "limited"
        depth_limit = "low" if depth_limit not in {"none", "low"} else depth_limit
        max_questions = min(max_questions, 0)
        rules.append("collapsed_low_depth_rule")

    confidence = float(output.working_hypothesis.confidence)
    if confidence < 0.55 or divergence_severity == "needs_review":
        status = "limited"
        if depth_limit in {"medium", "high"}:
            depth_limit = "low_to_medium"
        blocked_reasons.append("low_confidence_for_activation")
        rules.append("low_confidence_limited_mode")

    must_do = _dedupe(
        list(output.next_micro_shift.must_do or []),
        limit=6,
    )
    must_not_do = _dedupe(
        list(output.next_micro_shift.must_not_do or [])
        + list(diagnostic_card.avoid_list or [])
        + list(thread_state.must_avoid or []),
        limit=8,
    )

    if blocked_reasons:
        status = "blocked"

    trace = PlannerBridgeTrace(
        version="planner_bridge_trace_v1",
        builder="planner_bridge_candidate_v1",
        divergence_severity=divergence_severity,
        rules_applied=rules,
        warnings=[str(item) for item in input_contract.divergence.get("warnings", [])],
        expected_divergence=bool(input_contract.divergence.get("expected_divergence", False)),
    )
    return PlannerBridgeOutput(
        schema_version="planner_bridge_output_v1",
        status=status,
        activation_mode="shadow_only",
        apply_to_writer=False,
        apply_to_writer_contract=False,
        response_goal_candidate=str(output.next_micro_shift.response_goal),
        response_mode_candidate=str(output.next_micro_shift.response_mode),
        depth_limit=depth_limit,
        max_questions=max_questions,
        max_concepts=max_concepts,
        must_do_candidates=must_do,
        must_not_do_candidates=must_not_do,
        safety_constraints=safety_constraints,
        kb_constraints={
            "kb_usage_mode": kb_usage_mode,
            "must_not_quote_source": bool(output.trace.must_not_quote_source),
        },
        confidence=confidence,
        blocked_reasons=_dedupe(blocked_reasons, limit=10),
        guardrails=PlannerBridgeGuardrails(
            apply_to_writer=False,
            apply_to_writer_contract=False,
            activation_mode="shadow_only",
            user_path_effect="none",
        ),
        trace=trace,
    )
