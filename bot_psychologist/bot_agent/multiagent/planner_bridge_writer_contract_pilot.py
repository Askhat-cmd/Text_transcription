"""Writer-contract pilot overlay builder (compare-only, non-mutating)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts.diagnostic_card import DiagnosticCard
from .contracts.planner_bridge_compliance_v1 import PlannerBridgeComplianceShadow
from .contracts.planner_bridge_writer_contract_pilot_v1 import (
    PlannerBridgeWriterContractPilotInput,
    PlannerBridgeWriterContractPilotOverlay,
    PlannerBridgeWriterContractPilotResult,
    PlannerBridgeWriterContractPilotTrace,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .contracts.writer_contract import WriterContract


_DEPTH_ORDER = {
    "none": 0,
    "low": 1,
    "low_to_medium": 2,
    "medium": 3,
    "high": 4,
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


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


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable_payload(val) for key, val in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        return [_stable_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    return str(value)


def _stable_json(value: Any) -> str:
    normalized = _stable_payload(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_writer_contract(value: WriterContract | dict[str, Any]) -> str:
    payload = value.to_dict() if isinstance(value, WriterContract) else _safe_dict(value)
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _extract_candidate_constraints(
    *,
    compliance_shadow: dict[str, Any],
    writer_contract: WriterContract,
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> dict[str, Any]:
    candidate = _safe_dict(compliance_shadow.get("planner_bridge_candidate"))
    compatibility = _safe_dict(compliance_shadow.get("compatibility"))
    writer_move = _safe_dict(writer_contract.to_prompt_context().get("writer_move_instructions"))

    safety_context = bool(
        state_snapshot.safety_flag
        or thread_state.safety_active
        or state_snapshot.nervous_state in {"hyper", "hypo"}
    )

    depth_limit = str(candidate.get("depth_limit", writer_move.get("depth_limit", "low_to_medium")) or "low_to_medium")
    if depth_limit not in _DEPTH_ORDER:
        depth_limit = "low_to_medium"

    max_questions = int(candidate.get("max_questions", writer_move.get("max_questions", 1)) or 0)
    max_questions = max(0, max_questions)
    max_concepts = int(candidate.get("max_concepts", 1) or 1)
    max_concepts = max(1, max_concepts)

    if safety_context:
        if _DEPTH_ORDER.get(depth_limit, 2) > _DEPTH_ORDER["low"]:
            depth_limit = "low"
        max_questions = 0
        max_concepts = min(max_concepts, 1)

    kb_constraints = _safe_dict(candidate.get("kb_constraints"))
    kb_usage_mode = str(kb_constraints.get("kb_usage_mode", "none") or "none")
    if kb_usage_mode not in {"none", "internal_lens_only", "practice_candidate_only"}:
        kb_usage_mode = "none"

    must_do = _dedupe(
        _safe_list(candidate.get("must_do_candidates"))
        + _safe_list(writer_move.get("must_do"))
    )[:8]
    must_not_do = _dedupe(
        _safe_list(candidate.get("must_not_do_candidates"))
        + _safe_list(writer_move.get("must_not_do"))
        + _safe_list(getattr(diagnostic_card, "avoid_list", []))
        + _safe_list(thread_state.must_avoid)
    )[:12]

    if safety_context:
        must_not_do = _dedupe(
            must_not_do
            + [
                "do_not_analyze_deeply",
                "do_not_ask_multiple_questions",
            ]
        )

    response_goal = str(candidate.get("response_goal_candidate", "") or "")
    if not response_goal:
        response_goal = str(thread_state.response_goal or diagnostic_card.current_need or "clarify")

    response_mode = str(candidate.get("response_mode_candidate", "") or "")
    if not response_mode:
        response_mode = str(thread_state.response_mode or "reflect")

    if not compatibility.get("kb_boundary_compatible", True):
        kb_usage_mode = "none"

    return {
        "response_goal": response_goal,
        "response_mode": response_mode,
        "depth_limit": depth_limit,
        "max_questions": max_questions,
        "max_concepts": max_concepts,
        "must_do": must_do,
        "must_not_do": must_not_do,
        "kb_usage_mode": kb_usage_mode,
        "must_not_quote_source": True,
    }


def _build_risk_assessment(
    *,
    compliance_shadow: dict[str, Any],
    candidate_constraints: dict[str, Any],
    state_snapshot: StateSnapshot,
    thread_state: ThreadState,
) -> dict[str, str]:
    compatibility = _safe_dict(compliance_shadow.get("compatibility"))
    overall_status = str(compatibility.get("overall_status", "needs_review") or "needs_review")

    safety_context = bool(
        state_snapshot.safety_flag
        or thread_state.safety_active
        or state_snapshot.nervous_state in {"hyper", "hypo"}
    )
    safety_risk = "none"
    if safety_context:
        depth = str(candidate_constraints.get("depth_limit", "low_to_medium"))
        max_questions = int(candidate_constraints.get("max_questions", 0) or 0)
        if _DEPTH_ORDER.get(depth, 2) > _DEPTH_ORDER["low"] or max_questions > 0:
            safety_risk = "high"
        else:
            safety_risk = "low"

    kb_boundary_ok = bool(compatibility.get("kb_boundary_compatible", True))
    kb_boundary_risk = "none" if kb_boundary_ok else "high"

    must_do = set(_safe_list(candidate_constraints.get("must_do")))
    must_not_do = set(_safe_list(candidate_constraints.get("must_not_do")))
    contract_conflict_risk = "none"
    if must_do.intersection(must_not_do):
        contract_conflict_risk = "high"
    elif overall_status in {"needs_review", "expected_divergence"}:
        contract_conflict_risk = "medium"
    elif overall_status == "blocked":
        contract_conflict_risk = "high"

    activation_readiness = "pilot_ready"
    if overall_status == "blocked" or kb_boundary_risk == "high":
        activation_readiness = "blocked"
    elif safety_context or safety_risk in {"medium", "high"}:
        activation_readiness = "not_ready"

    return {
        "safety_risk": safety_risk,
        "contract_conflict_risk": contract_conflict_risk,
        "kb_boundary_risk": kb_boundary_risk,
        "activation_readiness": activation_readiness,
    }


def build_planner_bridge_writer_contract_pilot_v1(
    *,
    writer_contract: WriterContract,
    planner_bridge_compliance_shadow: PlannerBridgeComplianceShadow | dict[str, Any],
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> PlannerBridgeWriterContractPilotResult:
    compliance_shadow = (
        planner_bridge_compliance_shadow.to_dict()
        if isinstance(planner_bridge_compliance_shadow, PlannerBridgeComplianceShadow)
        else _safe_dict(planner_bridge_compliance_shadow)
    )

    _ = PlannerBridgeWriterContractPilotInput(
        writer_contract=writer_contract.to_dict(),
        planner_bridge_compliance_shadow=compliance_shadow,
        diagnostic_card=diagnostic_card.to_dict(),
        thread_state=thread_state.to_dict(),
        state_snapshot=state_snapshot.to_dict(),
    )

    hash_before = _hash_writer_contract(writer_contract)

    candidate_constraints = _extract_candidate_constraints(
        compliance_shadow=compliance_shadow,
        writer_contract=writer_contract,
        diagnostic_card=diagnostic_card,
        thread_state=thread_state,
        state_snapshot=state_snapshot,
    )
    risk_assessment = _build_risk_assessment(
        compliance_shadow=compliance_shadow,
        candidate_constraints=candidate_constraints,
        state_snapshot=state_snapshot,
        thread_state=thread_state,
    )

    overlay = PlannerBridgeWriterContractPilotOverlay(
        schema_version="planner_bridge_writer_contract_pilot_overlay_v1",
        activation_mode="pilot_shadow_only",
        apply_to_writer_contract=False,
        apply_to_writer_prompt=False,
        apply_to_final_answer=False,
        candidate_constraints=candidate_constraints,
        merge_policy={
            "mode": "non_mutating_compare_only",
            "allowed_fields": [],
            "blocked_fields": [
                "thread_state",
                "memory_bundle",
                "context_package",
                "diagnostic_card",
                "response_language",
                "writer_prompt",
                "final_answer",
            ],
        },
        risk_assessment=risk_assessment,
        guardrails={
            "writer_contract_changed": False,
            "writer_prompt_changed": False,
            "final_answer_changed": False,
            "provider_called": False,
        },
    )

    hash_after = _hash_writer_contract(writer_contract)
    writer_contract_changed = hash_before != hash_after

    blocked_reasons = _safe_list(compliance_shadow.get("blocked_reasons"))
    warnings = _safe_list(compliance_shadow.get("warnings"))
    if writer_contract_changed:
        blocked_reasons.append("writer_contract_mutated")
    if risk_assessment.get("activation_readiness") == "blocked":
        blocked_reasons.append("pilot_overlay_not_ready")

    trace_rules = [
        "pilot_shadow_only_guardrail",
        "non_mutating_compare_only",
        "writer_contract_hash_proof",
    ]
    if bool(state_snapshot.safety_flag or thread_state.safety_active):
        trace_rules.append("safety_context_checked")

    return PlannerBridgeWriterContractPilotResult(
        schema_version="planner_bridge_writer_contract_pilot_result_v1",
        overlay=overlay,
        writer_contract_hash_before_pilot=hash_before,
        writer_contract_hash_after_pilot=hash_after,
        writer_contract_changed_by_pilot=writer_contract_changed,
        blocked_reasons=_dedupe(blocked_reasons),
        warnings=_dedupe(warnings),
        trace=PlannerBridgeWriterContractPilotTrace(
            schema_version="planner_bridge_writer_contract_pilot_trace_v1",
            builder="planner_bridge_writer_contract_pilot_v1",
            rules_applied=trace_rules,
            warnings=_dedupe(warnings),
        ),
    )


def build_planner_bridge_writer_contract_pilot_runtime_shadow_v1(
    *,
    writer_contract: WriterContract,
    planner_bridge_compliance_shadow: dict[str, Any],
    diagnostic_card: DiagnosticCard,
    thread_state: ThreadState,
    state_snapshot: StateSnapshot,
) -> dict[str, Any]:
    """Build writer-contract pilot overlay for runtime debug only."""
    try:
        result = build_planner_bridge_writer_contract_pilot_v1(
            writer_contract=writer_contract,
            planner_bridge_compliance_shadow=planner_bridge_compliance_shadow,
            diagnostic_card=diagnostic_card,
            thread_state=thread_state,
            state_snapshot=state_snapshot,
        )
        return result.to_dict()
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": "planner_bridge_writer_contract_pilot_result_v1",
            "overlay": {
                "schema_version": "planner_bridge_writer_contract_pilot_overlay_v1",
                "activation_mode": "pilot_shadow_only",
                "apply_to_writer_contract": False,
                "apply_to_writer_prompt": False,
                "apply_to_final_answer": False,
                "candidate_constraints": {
                    "response_goal": "",
                    "response_mode": "reflect",
                    "depth_limit": "none",
                    "max_questions": 0,
                    "max_concepts": 1,
                    "must_do": [],
                    "must_not_do": [],
                    "kb_usage_mode": "none",
                    "must_not_quote_source": True,
                },
                "merge_policy": {
                    "mode": "non_mutating_compare_only",
                    "allowed_fields": [],
                    "blocked_fields": ["writer_prompt", "final_answer"],
                },
                "risk_assessment": {
                    "safety_risk": "high",
                    "contract_conflict_risk": "high",
                    "kb_boundary_risk": "high",
                    "activation_readiness": "blocked",
                },
                "guardrails": {
                    "writer_contract_changed": False,
                    "writer_prompt_changed": False,
                    "final_answer_changed": False,
                    "provider_called": False,
                },
            },
            "writer_contract_hash_before_pilot": "",
            "writer_contract_hash_after_pilot": "",
            "writer_contract_changed_by_pilot": False,
            "blocked_reasons": [f"writer_contract_pilot_failed:{exc.__class__.__name__}"],
            "warnings": [],
            "trace": {
                "schema_version": "planner_bridge_writer_contract_pilot_trace_v1",
                "builder": "planner_bridge_writer_contract_pilot_v1",
                "rules_applied": ["pilot_shadow_only_guardrail", "runtime_exception_fallback"],
                "warnings": [],
            },
        }
