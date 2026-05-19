"""Contracts for PRD-046.1.27 controlled cohort expansion execution gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ControlledCohortExpansionStatusV1:
    final_status: str = "failed"
    decision: str = "blocked_requires_hotfix"
    source_gate_passed: bool = False
    botdb_preflight_passed: bool = False
    cohort_policy_passed: bool = False
    target_user_count: int = 0
    scenario_count: int = 0
    provider_calls_total: int = 0
    provider_budget_gate_passed: bool = False
    normal_user_controls_total: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_calls: int = 0
    normal_user_no_effect_gate_passed: bool = False
    quality_micro_shift_gate_passed: bool = False
    micro_shift_present_rate: float = 0.0
    safety_kb_boundary_gate_passed: bool = False
    trace_provider_sanitization_gate_passed: bool = False
    rollback_precheck_passed: bool = False
    rollback_postcheck_passed: bool = False
    rollback_gate_passed: bool = False
    botdb_stability_gate_passed: bool = False
    hard_stop_triggered: bool = True
    production_mutation_detected: bool = True
    artifact_encoding_hygiene_passed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_requires_hotfix")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.botdb_preflight_passed = _as_bool(self.botdb_preflight_passed, False)
        self.cohort_policy_passed = _as_bool(self.cohort_policy_passed, False)
        self.target_user_count = _as_int(self.target_user_count, 0)
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.provider_budget_gate_passed = _as_bool(self.provider_budget_gate_passed, False)
        self.normal_user_controls_total = _as_int(self.normal_user_controls_total, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_calls = _as_int(self.normal_user_provider_calls, 0)
        self.normal_user_no_effect_gate_passed = _as_bool(self.normal_user_no_effect_gate_passed, False)
        self.quality_micro_shift_gate_passed = _as_bool(self.quality_micro_shift_gate_passed, False)
        self.micro_shift_present_rate = _as_float(self.micro_shift_present_rate, 0.0)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)
        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, False)
        self.rollback_precheck_passed = _as_bool(self.rollback_precheck_passed, False)
        self.rollback_postcheck_passed = _as_bool(self.rollback_postcheck_passed, False)
        self.rollback_gate_passed = _as_bool(self.rollback_gate_passed, False)
        self.botdb_stability_gate_passed = _as_bool(self.botdb_stability_gate_passed, False)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, True)
        self.production_mutation_detected = _as_bool(self.production_mutation_detected, True)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.next_recommended_prd = _as_str(self.next_recommended_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "botdb_preflight_passed": self.botdb_preflight_passed,
            "cohort_policy_passed": self.cohort_policy_passed,
            "target_user_count": self.target_user_count,
            "scenario_count": self.scenario_count,
            "provider_calls_total": self.provider_calls_total,
            "provider_budget_gate_passed": self.provider_budget_gate_passed,
            "normal_user_controls_total": self.normal_user_controls_total,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_calls": self.normal_user_provider_calls,
            "normal_user_no_effect_gate_passed": self.normal_user_no_effect_gate_passed,
            "quality_micro_shift_gate_passed": self.quality_micro_shift_gate_passed,
            "micro_shift_present_rate": self.micro_shift_present_rate,
            "safety_kb_boundary_gate_passed": self.safety_kb_boundary_gate_passed,
            "trace_provider_sanitization_gate_passed": self.trace_provider_sanitization_gate_passed,
            "rollback_precheck_passed": self.rollback_precheck_passed,
            "rollback_postcheck_passed": self.rollback_postcheck_passed,
            "rollback_gate_passed": self.rollback_gate_passed,
            "botdb_stability_gate_passed": self.botdb_stability_gate_passed,
            "hard_stop_triggered": self.hard_stop_triggered,
            "production_mutation_detected": self.production_mutation_detected,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "next_recommended_prd": self.next_recommended_prd,
        }


@dataclass
class ControlledCohortExpansionDecisionV1:
    schema_version: str = "diagnostic_center_controlled_cohort_expansion_decision_v1"
    prd_id: str = "PRD-046.1.27"
    final_status: str = "failed"
    decision: str = "blocked_requires_hotfix"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_cohort_expansion_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.27")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_requires_hotfix")
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]
        self.next_recommended_prd = _as_str(self.next_recommended_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "next_recommended_prd": self.next_recommended_prd,
        }


@dataclass
class ControlledCohortExpansionBundleV1:
    source_gate: dict[str, Any] = field(default_factory=dict)
    botdb_preflight: dict[str, Any] = field(default_factory=dict)
    cohort_policy: dict[str, Any] = field(default_factory=dict)
    provider_execution_evidence: dict[str, Any] = field(default_factory=dict)
    provider_budget_gate: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_gate: dict[str, Any] = field(default_factory=dict)
    quality_micro_shift_gate: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_gate: dict[str, Any] = field(default_factory=dict)
    trace_provider_sanitization_gate: dict[str, Any] = field(default_factory=dict)
    rollback_gate: dict[str, Any] = field(default_factory=dict)
    botdb_stability_gate: dict[str, Any] = field(default_factory=dict)
    hard_stop_gate: dict[str, Any] = field(default_factory=dict)
    no_mutation_proof: dict[str, Any] = field(default_factory=dict)
    artifact_encoding_hygiene: dict[str, Any] = field(default_factory=dict)
    decision_gate: dict[str, Any] = field(default_factory=dict)
    scorecard: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.botdb_preflight = _safe_dict(self.botdb_preflight)
        self.cohort_policy = _safe_dict(self.cohort_policy)
        self.provider_execution_evidence = _safe_dict(self.provider_execution_evidence)
        self.provider_budget_gate = _safe_dict(self.provider_budget_gate)
        self.normal_user_no_effect_gate = _safe_dict(self.normal_user_no_effect_gate)
        self.quality_micro_shift_gate = _safe_dict(self.quality_micro_shift_gate)
        self.safety_kb_boundary_gate = _safe_dict(self.safety_kb_boundary_gate)
        self.trace_provider_sanitization_gate = _safe_dict(self.trace_provider_sanitization_gate)
        self.rollback_gate = _safe_dict(self.rollback_gate)
        self.botdb_stability_gate = _safe_dict(self.botdb_stability_gate)
        self.hard_stop_gate = _safe_dict(self.hard_stop_gate)
        self.no_mutation_proof = _safe_dict(self.no_mutation_proof)
        self.artifact_encoding_hygiene = _safe_dict(self.artifact_encoding_hygiene)
        self.decision_gate = _safe_dict(self.decision_gate)
        self.scorecard = _safe_dict(self.scorecard)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "botdb_preflight": dict(self.botdb_preflight),
            "cohort_policy": dict(self.cohort_policy),
            "provider_execution_evidence": dict(self.provider_execution_evidence),
            "provider_budget_gate": dict(self.provider_budget_gate),
            "normal_user_no_effect_gate": dict(self.normal_user_no_effect_gate),
            "quality_micro_shift_gate": dict(self.quality_micro_shift_gate),
            "safety_kb_boundary_gate": dict(self.safety_kb_boundary_gate),
            "trace_provider_sanitization_gate": dict(self.trace_provider_sanitization_gate),
            "rollback_gate": dict(self.rollback_gate),
            "botdb_stability_gate": dict(self.botdb_stability_gate),
            "hard_stop_gate": dict(self.hard_stop_gate),
            "no_mutation_proof": dict(self.no_mutation_proof),
            "artifact_encoding_hygiene": dict(self.artifact_encoding_hygiene),
            "decision_gate": dict(self.decision_gate),
            "scorecard": dict(self.scorecard),
        }
