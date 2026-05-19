"""Contracts for PRD-046.1.30 controlled rollout planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_FINAL_STATUS = {"passed", "blocked", "warning"}
ALLOWED_DECISIONS = {
    "ready_for_controlled_rollout_execution_prd",
    "blocked_needs_hotfix",
    "blocked_needs_human_governance",
}


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


def _as_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ControlledRolloutPlanningSourceGate:
    schema_version: str = "diagnostic_center_controlled_rollout_planning_source_gate_v1"
    prd_id: str = "PRD-046.1.30"
    source_gate_passed: bool = False
    source_046_1_28_passed: bool = False
    source_046_1_29_passed: bool = False
    runtime_map_gate_passed: bool = False
    eval_harness_gate_passed: bool = False
    docs_compaction_gate_passed: bool = False
    blockers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_planning_source_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.source_046_1_28_passed = _as_bool(self.source_046_1_28_passed, False)
        self.source_046_1_29_passed = _as_bool(self.source_046_1_29_passed, False)
        self.runtime_map_gate_passed = _as_bool(self.runtime_map_gate_passed, False)
        self.eval_harness_gate_passed = _as_bool(self.eval_harness_gate_passed, False)
        self.docs_compaction_gate_passed = _as_bool(self.docs_compaction_gate_passed, False)
        self.blockers = [str(item) for item in _as_list(self.blockers)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "source_gate_passed": self.source_gate_passed,
            "source_046_1_28_passed": self.source_046_1_28_passed,
            "source_046_1_29_passed": self.source_046_1_29_passed,
            "runtime_map_gate_passed": self.runtime_map_gate_passed,
            "eval_harness_gate_passed": self.eval_harness_gate_passed,
            "docs_compaction_gate_passed": self.docs_compaction_gate_passed,
            "blockers": list(self.blockers),
        }


@dataclass
class ControlledRolloutCohortPolicy:
    schema_version: str = "diagnostic_center_controlled_rollout_cohort_policy_v1"
    prd_id: str = "PRD-046.1.30"
    max_target_users: int = 3
    target_user_type: str = "allowlisted_internal_or_synthetic_operators_only"
    normal_user_activation_allowed: bool = False
    broad_rollout_allowed: bool = False
    production_ready_allowed: bool = False
    requires_explicit_allowlist: bool = True
    requires_test_prefix_or_operator_marker: bool = True
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_cohort_policy_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.max_target_users = _as_int(self.max_target_users, 3, minimum=0)
        self.target_user_type = _as_str(self.target_user_type, "allowlisted_internal_or_synthetic_operators_only")
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready_allowed = _as_bool(self.production_ready_allowed, False)
        self.requires_explicit_allowlist = _as_bool(self.requires_explicit_allowlist, True)
        self.requires_test_prefix_or_operator_marker = _as_bool(self.requires_test_prefix_or_operator_marker, True)
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "max_target_users": self.max_target_users,
            "target_user_type": self.target_user_type,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready_allowed": self.production_ready_allowed,
            "requires_explicit_allowlist": self.requires_explicit_allowlist,
            "requires_test_prefix_or_operator_marker": self.requires_test_prefix_or_operator_marker,
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutToggleMatrix:
    schema_version: str = "diagnostic_center_controlled_rollout_toggle_matrix_v1"
    prd_id: str = "PRD-046.1.30"
    matrix: dict[str, Any] = field(default_factory=dict)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_toggle_matrix_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.matrix = _as_dict(self.matrix)
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "matrix": dict(self.matrix),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutPreflightGate:
    schema_version: str = "diagnostic_center_controlled_rollout_preflight_gate_v1"
    prd_id: str = "PRD-046.1.30"
    checks: list[dict[str, Any]] = field(default_factory=list)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_preflight_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.checks = [dict(item) for item in _as_list(self.checks) if isinstance(item, dict)]
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "checks": list(self.checks),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutHardStopCriteria:
    schema_version: str = "diagnostic_center_controlled_rollout_hard_stop_criteria_v1"
    prd_id: str = "PRD-046.1.30"
    hard_stops: list[str] = field(default_factory=list)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_hard_stop_criteria_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.hard_stops = [str(item) for item in _as_list(self.hard_stops)]
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "hard_stops": list(self.hard_stops),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutMonitoringPlan:
    schema_version: str = "diagnostic_center_controlled_rollout_monitoring_plan_v1"
    prd_id: str = "PRD-046.1.30"
    metrics: dict[str, str] = field(default_factory=dict)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_monitoring_plan_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        metrics = _as_dict(self.metrics)
        self.metrics = {str(k): str(v) for k, v in metrics.items()}
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "metrics": dict(self.metrics),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutRollbackPlan:
    schema_version: str = "diagnostic_center_controlled_rollout_rollback_plan_v1"
    prd_id: str = "PRD-046.1.30"
    rollback_steps: list[str] = field(default_factory=list)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_rollback_plan_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.rollback_steps = [str(item) for item in _as_list(self.rollback_steps)]
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "rollback_steps": list(self.rollback_steps),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutEvidencePlan:
    schema_version: str = "diagnostic_center_controlled_rollout_evidence_plan_v1"
    prd_id: str = "PRD-046.1.30"
    required_artifacts: list[str] = field(default_factory=list)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_evidence_plan_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.required_artifacts = [str(item) for item in _as_list(self.required_artifacts)]
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "required_artifacts": list(self.required_artifacts),
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutDecision:
    schema_version: str = "diagnostic_center_controlled_rollout_decision_v1"
    prd_id: str = "PRD-046.1.30"
    final_status: str = "blocked"
    decision: str = "blocked_needs_hotfix"
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    provider_execution_performed: bool = False
    provider_called: bool = False
    runtime_defaults_changed: bool = False
    production_data_mutated: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.final_status = _as_str(self.final_status, "blocked")
        if self.final_status not in ALLOWED_FINAL_STATUS:
            self.final_status = "blocked"
        self.decision = _as_str(self.decision, "blocked_needs_hotfix")
        if self.decision not in ALLOWED_DECISIONS:
            self.decision = "blocked_needs_hotfix"
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.provider_execution_performed = _as_bool(self.provider_execution_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "provider_execution_performed": self.provider_execution_performed,
            "provider_called": self.provider_called,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "production_data_mutated": self.production_data_mutated,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass
class ControlledRolloutPlanningScorecard:
    schema_version: str = "diagnostic_center_controlled_rollout_planning_scorecard_v1"
    prd_id: str = "PRD-046.1.30"
    final_status: str = "blocked"
    decision: str = "blocked_needs_hotfix"
    source_gate: str = "failed"
    runtime_map_gate: str = "failed"
    eval_harness_gate: str = "failed"
    cohort_policy_ready: bool = False
    toggle_matrix_ready: bool = False
    preflight_gates_ready: bool = False
    hard_stop_criteria_ready: bool = False
    rollback_plan_ready: bool = False
    monitoring_plan_ready: bool = False
    evidence_capture_plan_ready: bool = False
    normal_user_no_effect_plan_ready: bool = False
    provider_execution_performed: bool = False
    provider_called: bool = False
    runtime_defaults_changed: bool = False
    production_data_mutated: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    no_mutation_proof_passed: bool = False
    artifact_encoding_hygiene_passed: bool = False
    docs_synced: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_planning_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.30")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_needs_hotfix")
        self.source_gate = _as_str(self.source_gate, "failed")
        self.runtime_map_gate = _as_str(self.runtime_map_gate, "failed")
        self.eval_harness_gate = _as_str(self.eval_harness_gate, "failed")
        self.cohort_policy_ready = _as_bool(self.cohort_policy_ready, False)
        self.toggle_matrix_ready = _as_bool(self.toggle_matrix_ready, False)
        self.preflight_gates_ready = _as_bool(self.preflight_gates_ready, False)
        self.hard_stop_criteria_ready = _as_bool(self.hard_stop_criteria_ready, False)
        self.rollback_plan_ready = _as_bool(self.rollback_plan_ready, False)
        self.monitoring_plan_ready = _as_bool(self.monitoring_plan_ready, False)
        self.evidence_capture_plan_ready = _as_bool(self.evidence_capture_plan_ready, False)
        self.normal_user_no_effect_plan_ready = _as_bool(self.normal_user_no_effect_plan_ready, False)
        self.provider_execution_performed = _as_bool(self.provider_execution_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.docs_synced = _as_bool(self.docs_synced, False)
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate": self.source_gate,
            "runtime_map_gate": self.runtime_map_gate,
            "eval_harness_gate": self.eval_harness_gate,
            "cohort_policy_ready": self.cohort_policy_ready,
            "toggle_matrix_ready": self.toggle_matrix_ready,
            "preflight_gates_ready": self.preflight_gates_ready,
            "hard_stop_criteria_ready": self.hard_stop_criteria_ready,
            "rollback_plan_ready": self.rollback_plan_ready,
            "monitoring_plan_ready": self.monitoring_plan_ready,
            "evidence_capture_plan_ready": self.evidence_capture_plan_ready,
            "normal_user_no_effect_plan_ready": self.normal_user_no_effect_plan_ready,
            "provider_execution_performed": self.provider_execution_performed,
            "provider_called": self.provider_called,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "production_data_mutated": self.production_data_mutated,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "docs_synced": self.docs_synced,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


__all__ = [
    "ControlledRolloutPlanningSourceGate",
    "ControlledRolloutCohortPolicy",
    "ControlledRolloutToggleMatrix",
    "ControlledRolloutPreflightGate",
    "ControlledRolloutHardStopCriteria",
    "ControlledRolloutMonitoringPlan",
    "ControlledRolloutRollbackPlan",
    "ControlledRolloutEvidencePlan",
    "ControlledRolloutDecision",
    "ControlledRolloutPlanningScorecard",
]
