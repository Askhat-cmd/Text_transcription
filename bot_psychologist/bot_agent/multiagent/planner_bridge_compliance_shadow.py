"""Planner Bridge vs Writer Move compliance comparison in shadow mode only."""

from __future__ import annotations

from typing import Any

from .contracts.diagnostic_card import DiagnosticCard
from .contracts.diagnostic_center_v1 import DiagnosticCenterOutput
from .contracts.planner_bridge_compliance_v1 import PlannerBridgeComplianceShadow
from .contracts.planner_bridge_v1 import PlannerBridgeOutput
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .diagnostic_center_divergence import classify_divergence_severity_v1
from .planner_bridge_candidate import build_planner_bridge_candidate_v1
from .writer_move_compliance import build_writer_move_instructions_v1


_DEPTH_ORDER = {
    "none": 0,
    "low": 1,
    "low_to_medium": 2,
    "medium": 3,
    "high": 4,
}


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _writer_expected_depth(move: str) -> str:
    if move in {"safe_override", "regulate_first"}:
        return "low"
    if move in {"validate_briefly", "offer_one_micro_step"}:
        return "low_to_medium"
    return "medium"


def _is_safety_context(
    *,
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
    bridge: dict[str, Any],
) -> bool:
    if bool(state_snapshot.safety_flag or thread_state.safety_active):
        return True
    if state_snapshot.nervous_state in {"hyper", "hypo"}:
        return True
    if str(bridge.get("status")) == "limited" and "safety_first" in _safe_list(
        bridge.get("safety_constraints")
    ):
        return True
    return False


def _move_goal_compatible(move: str, goal: str) -> bool:
    if move in {"safe_override", "regulate_first"}:
        return goal in {"safety_redirect", "ground_and_reduce_load"}
    if move == "offer_one_micro_step":
        return goal in {"clarify_before_action", "clarify"}
    if move in {"clarify_one_point", "reflect_pattern_once", "explore_carefully"}:
        return goal in {
            "clarify",
            "stabilize_authorship",
            "deepen_and_integrate",
            "decenter_without_shaming",
            "ground_and_reduce_load",
        }
    return True


def build_planner_bridge_compliance_shadow_v1(
    *,
    writer_move_instructions: dict[str, Any],
    planner_bridge_output: PlannerBridgeOutput | dict[str, Any],
    diagnostic_card: DiagnosticCard,
    divergence: dict[str, Any],
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> PlannerBridgeComplianceShadow:
    bridge = (
        planner_bridge_output.to_dict()
        if isinstance(planner_bridge_output, PlannerBridgeOutput)
        else _safe_dict(planner_bridge_output)
    )
    move = str(writer_move_instructions.get("move", "validate_briefly") or "validate_briefly")
    writer_max_questions = int(writer_move_instructions.get("max_questions", 1) or 1)
    writer_must_do = _safe_list(writer_move_instructions.get("must_do"))
    writer_must_not = _safe_list(writer_move_instructions.get("must_not_do"))

    bridge_depth = str(bridge.get("depth_limit", "low_to_medium") or "low_to_medium")
    bridge_max_questions = int(bridge.get("max_questions", 1) or 1)
    bridge_must_do = _safe_list(bridge.get("must_do_candidates"))
    bridge_must_not = _safe_list(bridge.get("must_not_do_candidates"))
    bridge_goal = str(bridge.get("response_goal_candidate", "") or "")
    bridge_status = str(bridge.get("status", "candidate") or "candidate")
    kb_constraints = _safe_dict(bridge.get("kb_constraints"))
    kb_mode = str(kb_constraints.get("kb_usage_mode", "none") or "none")
    must_not_quote_source = bool(kb_constraints.get("must_not_quote_source", True))

    safety_context = _is_safety_context(
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        bridge=bridge,
    )
    safety_compatible = True
    if safety_context:
        safety_compatible = (
            bridge_status in {"limited", "blocked"} and bridge_depth in {"none", "low"}
        )

    writer_expected_depth = _writer_expected_depth(move)
    depth_compatible = _DEPTH_ORDER.get(bridge_depth, 2) <= _DEPTH_ORDER.get(writer_expected_depth, 2)
    question_limit_compatible = bridge_max_questions <= writer_max_questions
    writer_move_candidate_compatible = _move_goal_compatible(move, bridge_goal)
    kb_boundary_compatible = kb_mode in {
        "none",
        "internal_lens_only",
        "practice_candidate_only",
    } and must_not_quote_source and bool(divergence.get("kb_boundary_ok", True)) and not bool(
        divergence.get("raw_kb_text_exposed", False)
    )

    must_not_conflicts = set(bridge_must_do).intersection(set(writer_must_not))
    must_not_conflicts.update(set(writer_must_do).intersection(set(bridge_must_not)))
    must_not_conflict_count = len(must_not_conflicts)

    tightened_question_limit = bridge_max_questions < writer_max_questions
    tightened_depth = _DEPTH_ORDER.get(bridge_depth, 2) < _DEPTH_ORDER.get(writer_expected_depth, 2)
    added_must_not_do = [item for item in bridge_must_not if item not in writer_must_not]
    added_must_do = [item for item in bridge_must_do if item not in writer_must_do]

    blocked_reasons: list[str] = _safe_list(bridge.get("blocked_reasons"))
    rules_applied: list[str] = ["shadow_compare_only_guardrail"]
    warnings: list[str] = []

    if bridge.get("apply_to_writer") or bridge.get("apply_to_writer_contract"):
        blocked_reasons.append("bridge_apply_to_writer_violation")
    if not kb_boundary_compatible:
        blocked_reasons.append("kb_boundary_violation")
    if not safety_compatible:
        blocked_reasons.append("safety_incompatible")
    if not depth_compatible and safety_context:
        blocked_reasons.append("unsafe_depth_in_safety_context")

    if not writer_move_candidate_compatible:
        warnings.append("writer_move_candidate_mismatch")
    if must_not_conflict_count > 0:
        warnings.append("must_not_conflict")
    if not question_limit_compatible:
        warnings.append("question_limit_not_compatible")

    expected_divergence = bool(_safe_dict(bridge.get("trace")).get("expected_divergence", False))
    overall_status = "compatible"
    if blocked_reasons:
        overall_status = "blocked"
    elif expected_divergence:
        overall_status = "expected_divergence"
    elif tightened_question_limit or tightened_depth or added_must_not_do:
        overall_status = "tightens_constraints"
    elif warnings:
        overall_status = "needs_review"

    if overall_status == "tightens_constraints":
        rules_applied.append("tightening_detected")
    if overall_status == "expected_divergence":
        rules_applied.append("expected_divergence_detected")
    if overall_status == "blocked":
        rules_applied.append("blocked_by_guardrails")
    if safety_context:
        rules_applied.append("safety_context_checked")

    return PlannerBridgeComplianceShadow(
        schema_version="planner_bridge_compliance_shadow_v1",
        activation_mode="shadow_compare_only",
        apply_to_writer=False,
        apply_to_writer_contract=False,
        writer_prompt_changed=False,
        final_answer_changed=False,
        existing_writer_move={
            "move": move,
            "max_sentences": int(writer_move_instructions.get("max_sentences", 5) or 5),
            "max_questions": writer_max_questions,
            "style": str(writer_move_instructions.get("style", "brief_supportive") or "brief_supportive"),
            "must_do": writer_must_do,
            "must_not_do": writer_must_not,
        },
        planner_bridge_candidate={
            "status": bridge_status,
            "response_goal_candidate": bridge_goal,
            "response_mode_candidate": str(bridge.get("response_mode_candidate", "") or ""),
            "depth_limit": bridge_depth,
            "max_questions": bridge_max_questions,
            "max_concepts": int(bridge.get("max_concepts", 1) or 1),
            "must_do_candidates": bridge_must_do,
            "must_not_do_candidates": bridge_must_not,
            "kb_constraints": {
                "kb_usage_mode": kb_mode,
                "must_not_quote_source": must_not_quote_source,
            },
        },
        compatibility={
            "safety_compatible": safety_compatible,
            "depth_compatible": depth_compatible,
            "question_limit_compatible": question_limit_compatible,
            "must_not_conflict_count": must_not_conflict_count,
            "writer_move_candidate_compatible": writer_move_candidate_compatible,
            "kb_boundary_compatible": kb_boundary_compatible,
            "overall_status": overall_status,
        },
        candidate_delta={
            "tightened_question_limit": tightened_question_limit,
            "tightened_depth": tightened_depth,
            "added_must_not_do": _dedupe(added_must_not_do),
            "added_must_do": _dedupe(added_must_do),
            "removed_constraints": [],
        },
        blocked_reasons=_dedupe(blocked_reasons),
        warnings=_dedupe(warnings),
        trace={
            "builder": "planner_bridge_compliance_shadow_v1",
            "rules_applied": _dedupe(rules_applied),
            "source": "shadow_compare_only",
            "diagnostic_move": diagnostic_card.suggested_writer_move,
        },
    )


def build_planner_bridge_compliance_runtime_shadow_v1(
    *,
    diagnostic_center_shadow: dict[str, Any],
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> dict[str, Any]:
    """Build candidate + compliance compare trace for runtime debug only."""
    try:
        output_raw = _safe_dict(diagnostic_center_shadow.get("output"))
        if not output_raw:
            return {
                "planner_bridge_candidate": {
                    "status": "unavailable",
                    "activation_mode": "shadow_only",
                    "apply_to_writer": False,
                    "apply_to_writer_contract": False,
                },
                "planner_bridge_compliance_shadow": {
                    "schema_version": "planner_bridge_compliance_shadow_v1",
                    "activation_mode": "shadow_compare_only",
                    "apply_to_writer": False,
                    "apply_to_writer_contract": False,
                    "writer_prompt_changed": False,
                    "final_answer_changed": False,
                    "compatibility": {"overall_status": "blocked"},
                    "blocked_reasons": ["diagnostic_center_shadow_output_missing"],
                },
            }
        divergence = _safe_dict(diagnostic_center_shadow.get("divergence"))
        output = DiagnosticCenterOutput.from_dict(output_raw)
        divergence_severity = classify_divergence_severity_v1(divergence)
        bridge = build_planner_bridge_candidate_v1(
            diagnostic_center_output=output,
            divergence=divergence,
            divergence_severity=divergence_severity,
            diagnostic_card=diagnostic_card,
            thread_state=thread_state,
            state_snapshot=state_snapshot,
        )
        instructions = build_writer_move_instructions_v1(diagnostic_card)
        compliance = build_planner_bridge_compliance_shadow_v1(
            writer_move_instructions=instructions,
            planner_bridge_output=bridge,
            diagnostic_card=diagnostic_card,
            divergence=divergence,
            thread_state=thread_state,
            state_snapshot=state_snapshot,
        )
        return {
            "planner_bridge_candidate": bridge.to_dict(),
            "planner_bridge_compliance_shadow": compliance.to_dict(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "planner_bridge_candidate": {
                "status": "error",
                "activation_mode": "shadow_only",
                "apply_to_writer": False,
                "apply_to_writer_contract": False,
                "error": f"planner_bridge_candidate_failed:{exc.__class__.__name__}",
            },
            "planner_bridge_compliance_shadow": {
                "schema_version": "planner_bridge_compliance_shadow_v1",
                "activation_mode": "shadow_compare_only",
                "apply_to_writer": False,
                "apply_to_writer_contract": False,
                "writer_prompt_changed": False,
                "final_answer_changed": False,
                "compatibility": {"overall_status": "blocked"},
                "blocked_reasons": [f"planner_bridge_compliance_failed:{exc.__class__.__name__}"],
            },
        }

