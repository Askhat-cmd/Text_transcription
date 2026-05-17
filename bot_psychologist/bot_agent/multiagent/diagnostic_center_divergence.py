"""Diagnostic Center shadow divergence evaluation and taxonomy."""

from __future__ import annotations

from typing import Any

from .contracts.diagnostic_card import DiagnosticCard
from .contracts.diagnostic_center_v1 import DiagnosticCenterOutput
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _as_bool(value: Any) -> bool:
    return bool(value)


def evaluate_diagnostic_center_divergence_v1(
    *,
    diagnostic_card: DiagnosticCard,
    diagnostic_center_output: DiagnosticCenterOutput,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
    kb_sanitization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expected_safety = bool(state_snapshot.safety_flag or thread_state.safety_active) or (
        state_snapshot.nervous_state in {"hyper", "hypo"}
    )
    depth_allowed = diagnostic_center_output.next_micro_shift.depth_allowed
    safety_priority_match = (
        diagnostic_center_output.status == "safety_first"
        if expected_safety
        else diagnostic_center_output.status in {"ok", "safety_first"}
    )
    depth_compatible = True
    if expected_safety:
        depth_compatible = depth_allowed in {"none", "low"}
    elif thread_state.ok_position == "I-W-" and thread_state.openness == "collapsed":
        depth_compatible = depth_allowed in {"none", "low"}

    move = diagnostic_card.suggested_writer_move
    goal = diagnostic_center_output.next_micro_shift.response_goal
    writer_move_compatible = True
    if move in {"safe_override", "regulate_first"}:
        writer_move_compatible = goal in {"safety_redirect", "ground_and_reduce_load"}
    elif move == "offer_one_micro_step":
        writer_move_compatible = goal in {"clarify_before_action", "clarify"}
    elif move in {"clarify_one_point", "reflect_pattern_once"}:
        writer_move_compatible = goal in {
            "stabilize_authorship",
            "clarify",
            "deepen_and_integrate",
            "decenter_without_shaming",
        }

    response_mode_compatible = True
    if thread_state.response_mode == "safe_override":
        response_mode_compatible = diagnostic_center_output.next_micro_shift.response_mode in {
            "ground_then_one_step",
            "minimal_support",
        }
    relation_to_thread_match = diagnostic_center_output.relation_to_thread == thread_state.relation_to_thread
    phase_match = diagnostic_center_output.phase == thread_state.phase
    pattern_core_present = bool(str(thread_state.pattern_core or "").strip())
    kb_usage_mode = diagnostic_center_output.trace.kb_usage_mode
    must_not_quote_source = bool(diagnostic_center_output.trace.must_not_quote_source)
    raw_kb_text_exposed = bool(_safe_dict(kb_sanitization).get("raw_kb_text_exposed", False))
    kb_boundary_ok = kb_usage_mode in {"internal_lens_only", "disabled", "practice_candidate_only"} and must_not_quote_source and not raw_kb_text_exposed
    thread_risk = "none"
    if not relation_to_thread_match and pattern_core_present:
        thread_risk = "zigzag"
    elif not relation_to_thread_match and not pattern_core_present:
        thread_risk = "topic_drift"
    elif not phase_match:
        thread_risk = "premature_depth"

    expected_divergence = False
    if move in {"safe_override", "regulate_first"} and goal == "safety_redirect":
        expected_divergence = True
    if thread_state.relation_to_thread == "branch" and pattern_core_present:
        expected_divergence = True
    if kb_usage_mode in {"internal_lens_only", "practice_candidate_only"}:
        expected_divergence = expected_divergence or bool(diagnostic_center_output.lens_signals)

    warnings: list[str] = []
    if not writer_move_compatible:
        warnings.append("writer_move_compatible_false")
    if not response_mode_compatible:
        warnings.append("response_mode_compatible_false")
    if not phase_match:
        warnings.append("phase_match_false")
    if not pattern_core_present:
        warnings.append("pattern_core_missing")
    if not relation_to_thread_match:
        warnings.append("relation_to_thread_mismatch")

    user_path = {
        "writer_contract_changed": False,
        "writer_prompt_changed_by_shadow": False,
        "final_answer_changed_by_shadow": False,
        "diagnostic_center_output_passed_to_writer": False,
    }
    hard_blocker_reasons: list[str] = []
    if not safety_priority_match:
        hard_blocker_reasons.append("safety_priority_mismatch")
    if expected_safety and not depth_compatible:
        hard_blocker_reasons.append("unsafe_depth_in_safety_context")
    if not kb_boundary_ok:
        hard_blocker_reasons.append("kb_boundary_violation")
    if raw_kb_text_exposed:
        hard_blocker_reasons.append("raw_kb_text_exposed")
    if user_path["writer_prompt_changed_by_shadow"]:
        hard_blocker_reasons.append("writer_prompt_changed_by_shadow")
    if user_path["diagnostic_center_output_passed_to_writer"]:
        hard_blocker_reasons.append("diagnostic_center_output_passed_to_writer")
    if user_path["final_answer_changed_by_shadow"]:
        hard_blocker_reasons.append("final_answer_changed_by_shadow")

    confidence = float(diagnostic_center_output.working_hypothesis.confidence)
    return {
        "safety_priority_match": bool(safety_priority_match),
        "depth_compatible": bool(depth_compatible),
        "writer_move_compatible": bool(writer_move_compatible),
        "response_mode_compatible": bool(response_mode_compatible),
        "relation_to_thread_match": bool(relation_to_thread_match),
        "phase_match": bool(phase_match),
        "pattern_core_present": bool(pattern_core_present),
        "kb_boundary_ok": bool(kb_boundary_ok),
        "raw_kb_text_exposed": bool(raw_kb_text_exposed),
        "thread_risk": thread_risk,
        "warnings": warnings,
        "hard_blocker_reasons": hard_blocker_reasons,
        "expected_divergence": bool(expected_divergence),
        "confidence": confidence,
        "diagnostic_card_alignment": {
            "safety_priority_match": bool(safety_priority_match),
            "low_resource_depth_match": bool(depth_compatible),
            "writer_move_compatible": bool(writer_move_compatible),
            "response_mode_compatible": bool(response_mode_compatible),
        },
        "thread_alignment": {
            "relation_to_thread_match": bool(relation_to_thread_match),
            "phase_match": bool(phase_match),
            "pattern_core_present": bool(pattern_core_present),
            "continuity_risk": thread_risk,
        },
        "kb_boundary": {
            "kb_usage_mode": kb_usage_mode,
            "must_not_quote_source": must_not_quote_source,
            "raw_kb_text_exposed": bool(raw_kb_text_exposed),
        },
        "user_path": user_path,
    }


def classify_divergence_severity_v1(divergence: dict[str, Any]) -> str:
    warnings = _safe_list(divergence.get("warnings"))
    hard_blockers = _safe_list(divergence.get("hard_blocker_reasons"))
    expected_divergence = _as_bool(divergence.get("expected_divergence", False))
    confidence = float(divergence.get("confidence", 1.0) or 1.0)
    if hard_blockers:
        return "hard_blocker"
    if expected_divergence:
        return "expected_divergence"
    if confidence < 0.55:
        return "needs_review"
    if len(warnings) >= 2:
        return "needs_review"
    if warnings:
        return "soft_warning"
    return "compatible"


def build_shadow_divergence_scorecard_v1(
    *,
    case_results: list[dict[str, Any]],
    prd: str,
    schema_version: str = "diagnostic_center_shadow_divergence_scorecard_v1",
) -> dict[str, Any]:
    total = len(case_results)
    hard = 0
    soft = 0
    expected = 0
    review = 0
    compatible = 0
    for item in case_results:
        severity = str(item.get("divergence_severity", "compatible"))
        if severity == "hard_blocker":
            hard += 1
        elif severity == "soft_warning":
            soft += 1
        elif severity == "expected_divergence":
            expected += 1
        elif severity == "needs_review":
            review += 1
        else:
            compatible += 1
    return {
        "schema_version": schema_version,
        "prd": prd,
        "cases_total": total,
        "hard_blocker_count": hard,
        "soft_warning_count": soft,
        "expected_divergence_count": expected,
        "needs_review_count": review,
        "compatible_count": compatible,
    }
