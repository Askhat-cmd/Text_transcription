"""Contracts for PRD-046.1.19 runtime pilot readiness planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class DiagnosticCenterRuntimePilotReadinessStatus:
    final_status: str = "failed"
    decision: str = "blocked_runtime_pilot_readiness"
    source_gate_passed: bool = False
    pilot_scope_ready: bool = False
    cohort_policy_ready: bool = False
    toggle_matrix_ready: bool = False
    runtime_preflight_requirements_ready: bool = False
    limited_live_smoke_plan_ready: bool = False
    rollback_first_runbook_ready: bool = False
    hard_stop_criteria_ready: bool = False
    monitoring_artifact_contract_ready: bool = False
    normal_user_guard_passed: bool = False
    kb_governance_guard_passed: bool = False
    trace_sanitization_guard_passed: bool = False
    execution_performed: bool = False
    runtime_activation_performed: bool = False
    provider_called: bool = False
    broad_rollout_allowed: bool = False
    normal_user_apply_allowed: bool = False
    future_execution_requires_new_prd: bool = True

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_runtime_pilot_readiness")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.pilot_scope_ready = _as_bool(self.pilot_scope_ready, False)
        self.cohort_policy_ready = _as_bool(self.cohort_policy_ready, False)
        self.toggle_matrix_ready = _as_bool(self.toggle_matrix_ready, False)
        self.runtime_preflight_requirements_ready = _as_bool(self.runtime_preflight_requirements_ready, False)
        self.limited_live_smoke_plan_ready = _as_bool(self.limited_live_smoke_plan_ready, False)
        self.rollback_first_runbook_ready = _as_bool(self.rollback_first_runbook_ready, False)
        self.hard_stop_criteria_ready = _as_bool(self.hard_stop_criteria_ready, False)
        self.monitoring_artifact_contract_ready = _as_bool(self.monitoring_artifact_contract_ready, False)
        self.normal_user_guard_passed = _as_bool(self.normal_user_guard_passed, False)
        self.kb_governance_guard_passed = _as_bool(self.kb_governance_guard_passed, False)
        self.trace_sanitization_guard_passed = _as_bool(self.trace_sanitization_guard_passed, False)
        self.execution_performed = _as_bool(self.execution_performed, False)
        self.runtime_activation_performed = _as_bool(self.runtime_activation_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.normal_user_apply_allowed = _as_bool(self.normal_user_apply_allowed, False)
        self.future_execution_requires_new_prd = _as_bool(self.future_execution_requires_new_prd, True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "pilot_scope_ready": self.pilot_scope_ready,
            "cohort_policy_ready": self.cohort_policy_ready,
            "toggle_matrix_ready": self.toggle_matrix_ready,
            "runtime_preflight_requirements_ready": self.runtime_preflight_requirements_ready,
            "limited_live_smoke_plan_ready": self.limited_live_smoke_plan_ready,
            "rollback_first_runbook_ready": self.rollback_first_runbook_ready,
            "hard_stop_criteria_ready": self.hard_stop_criteria_ready,
            "monitoring_artifact_contract_ready": self.monitoring_artifact_contract_ready,
            "normal_user_guard_passed": self.normal_user_guard_passed,
            "kb_governance_guard_passed": self.kb_governance_guard_passed,
            "trace_sanitization_guard_passed": self.trace_sanitization_guard_passed,
            "execution_performed": self.execution_performed,
            "runtime_activation_performed": self.runtime_activation_performed,
            "provider_called": self.provider_called,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "normal_user_apply_allowed": self.normal_user_apply_allowed,
            "future_execution_requires_new_prd": self.future_execution_requires_new_prd,
        }


@dataclass
class DiagnosticCenterRuntimePilotReadinessDecision:
    schema_version: str = "diagnostic_center_runtime_pilot_readiness_decision_v1"
    prd_id: str = "PRD-046.1.19"
    final_status: str = "failed"
    decision: str = "blocked_runtime_pilot_readiness"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = "PRD-046.1.19-HF1 - Runtime Pilot Readiness blocker hotfix"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_runtime_pilot_readiness_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.19")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_runtime_pilot_readiness")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.recommended_next_prd = _as_str(self.recommended_next_prd, "PRD-046.1.19-HF1 - Runtime Pilot Readiness blocker hotfix")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "recommended_next_prd": self.recommended_next_prd,
        }


@dataclass
class DiagnosticCenterRuntimePilotReadinessBundle:
    source_gate: dict[str, Any] = field(default_factory=dict)
    pilot_scope: dict[str, Any] = field(default_factory=dict)
    cohort_policy: dict[str, Any] = field(default_factory=dict)
    toggle_matrix: dict[str, Any] = field(default_factory=dict)
    runtime_preflight_requirements: dict[str, Any] = field(default_factory=dict)
    limited_live_smoke_plan: dict[str, Any] = field(default_factory=dict)
    rollback_first_runbook: dict[str, Any] = field(default_factory=dict)
    hard_stop_criteria: dict[str, Any] = field(default_factory=dict)
    monitoring_artifact_contract: dict[str, Any] = field(default_factory=dict)
    normal_user_guard: dict[str, Any] = field(default_factory=dict)
    kb_governance_guard: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_guard: dict[str, Any] = field(default_factory=dict)
    no_mutation_status: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene_status: dict[str, Any] = field(default_factory=dict)
    readiness_decision: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.pilot_scope = _safe_dict(self.pilot_scope)
        self.cohort_policy = _safe_dict(self.cohort_policy)
        self.toggle_matrix = _safe_dict(self.toggle_matrix)
        self.runtime_preflight_requirements = _safe_dict(self.runtime_preflight_requirements)
        self.limited_live_smoke_plan = _safe_dict(self.limited_live_smoke_plan)
        self.rollback_first_runbook = _safe_dict(self.rollback_first_runbook)
        self.hard_stop_criteria = _safe_dict(self.hard_stop_criteria)
        self.monitoring_artifact_contract = _safe_dict(self.monitoring_artifact_contract)
        self.normal_user_guard = _safe_dict(self.normal_user_guard)
        self.kb_governance_guard = _safe_dict(self.kb_governance_guard)
        self.trace_sanitization_guard = _safe_dict(self.trace_sanitization_guard)
        self.no_mutation_status = _safe_dict(self.no_mutation_status)
        self.artifact_hygiene_status = _safe_dict(self.artifact_hygiene_status)
        self.readiness_decision = _safe_dict(self.readiness_decision)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "pilot_scope": dict(self.pilot_scope),
            "cohort_policy": dict(self.cohort_policy),
            "toggle_matrix": dict(self.toggle_matrix),
            "runtime_preflight_requirements": dict(self.runtime_preflight_requirements),
            "limited_live_smoke_plan": dict(self.limited_live_smoke_plan),
            "rollback_first_runbook": dict(self.rollback_first_runbook),
            "hard_stop_criteria": dict(self.hard_stop_criteria),
            "monitoring_artifact_contract": dict(self.monitoring_artifact_contract),
            "normal_user_guard": dict(self.normal_user_guard),
            "kb_governance_guard": dict(self.kb_governance_guard),
            "trace_sanitization_guard": dict(self.trace_sanitization_guard),
            "no_mutation_status": dict(self.no_mutation_status),
            "artifact_hygiene_status": dict(self.artifact_hygiene_status),
            "readiness_decision": dict(self.readiness_decision),
        }


@dataclass
class DiagnosticCenterPilotCohortPolicy:
    max_initial_cohort_size: int = 1
    allowed_user_ids: list[str] = field(default_factory=lambda: ["pilot_runtime_operator_001"])
    normal_user_control_count: int = 2
    normal_user_apply_allowed: bool = False
    test_user_prefix: str = "pilot_"
    operator_user_required: bool = True

    def __post_init__(self) -> None:
        self.max_initial_cohort_size = _as_int(self.max_initial_cohort_size, 1)
        self.allowed_user_ids = [str(item) for item in _as_list(self.allowed_user_ids)]
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 2)
        self.normal_user_apply_allowed = _as_bool(self.normal_user_apply_allowed, False)
        self.test_user_prefix = _as_str(self.test_user_prefix, "pilot_")
        self.operator_user_required = _as_bool(self.operator_user_required, True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_initial_cohort_size": self.max_initial_cohort_size,
            "allowed_user_ids": list(self.allowed_user_ids),
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_allowed": self.normal_user_apply_allowed,
            "test_user_prefix": self.test_user_prefix,
            "operator_user_required": self.operator_user_required,
        }
