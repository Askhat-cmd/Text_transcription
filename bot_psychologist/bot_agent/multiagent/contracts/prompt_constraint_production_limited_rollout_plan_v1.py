"""Contracts for PRD-046.1.12 production-limited rollout planning gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class PromptConstraintProductionLimitedCohortPolicyV1:
    stage: str = "production_limited_plan_only"
    execution_allowed_in_this_prd: bool = False
    max_initial_real_user_count: int = 1
    max_total_users_in_first_execution_prd: int = 2
    allowlist_required: bool = True
    manual_operator_approval_required: bool = True
    automatic_enrollment_allowed: bool = False
    normal_user_default_path_unchanged: bool = True
    excluded_user_categories: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.stage = _as_str(self.stage, "production_limited_plan_only")
        self.execution_allowed_in_this_prd = _as_bool(self.execution_allowed_in_this_prd, False)
        self.max_initial_real_user_count = _as_int(self.max_initial_real_user_count, 1, minimum=0)
        self.max_total_users_in_first_execution_prd = _as_int(self.max_total_users_in_first_execution_prd, 2, minimum=0)
        self.allowlist_required = _as_bool(self.allowlist_required, True)
        self.manual_operator_approval_required = _as_bool(self.manual_operator_approval_required, True)
        self.automatic_enrollment_allowed = _as_bool(self.automatic_enrollment_allowed, False)
        self.normal_user_default_path_unchanged = _as_bool(self.normal_user_default_path_unchanged, True)
        self.excluded_user_categories = [str(item) for item in _as_list(self.excluded_user_categories)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "execution_allowed_in_this_prd": bool(self.execution_allowed_in_this_prd),
            "max_initial_real_user_count": int(self.max_initial_real_user_count),
            "max_total_users_in_first_execution_prd": int(self.max_total_users_in_first_execution_prd),
            "allowlist_required": bool(self.allowlist_required),
            "manual_operator_approval_required": bool(self.manual_operator_approval_required),
            "automatic_enrollment_allowed": bool(self.automatic_enrollment_allowed),
            "normal_user_default_path_unchanged": bool(self.normal_user_default_path_unchanged),
            "excluded_user_categories": list(self.excluded_user_categories),
        }


@dataclass
class PromptConstraintProductionLimitedPreflightGateV1:
    required_before_execution: dict[str, Any] = field(default_factory=dict)
    blocked_if: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.required_before_execution = _safe_dict(self.required_before_execution)
        self.blocked_if = [str(item) for item in _as_list(self.blocked_if)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_before_execution": dict(self.required_before_execution),
            "blocked_if": list(self.blocked_if),
        }


@dataclass
class PromptConstraintProductionLimitedOperatorChecklistV1:
    checklist: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.checklist = [dict(item) for item in _as_list(self.checklist) if isinstance(item, dict)]

    def to_dict(self) -> dict[str, Any]:
        return {"checklist": list(self.checklist)}


@dataclass
class PromptConstraintProductionLimitedMonitoringPlanV1:
    metrics: dict[str, Any] = field(default_factory=dict)
    trace_requirements: dict[str, Any] = field(default_factory=dict)
    observation_window: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metrics = _safe_dict(self.metrics)
        self.trace_requirements = _safe_dict(self.trace_requirements)
        self.observation_window = _safe_dict(self.observation_window)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": dict(self.metrics),
            "trace_requirements": dict(self.trace_requirements),
            "observation_window": dict(self.observation_window),
        }


@dataclass
class PromptConstraintProductionLimitedRollbackPlanV1:
    rollback_priority: str = "force_disabled_absolute_priority"
    primary_rollback: dict[str, Any] = field(default_factory=dict)
    secondary_rollback: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    reporting: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.rollback_priority = _as_str(self.rollback_priority, "force_disabled_absolute_priority")
        self.primary_rollback = _safe_dict(self.primary_rollback)
        self.secondary_rollback = _safe_dict(self.secondary_rollback)
        self.verification = _safe_dict(self.verification)
        self.reporting = _safe_dict(self.reporting)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_priority": self.rollback_priority,
            "primary_rollback": dict(self.primary_rollback),
            "secondary_rollback": dict(self.secondary_rollback),
            "verification": dict(self.verification),
            "reporting": dict(self.reporting),
        }


@dataclass
class PromptConstraintProductionLimitedAbortCriteriaV1:
    hard_abort_if: list[str] = field(default_factory=list)
    warning_if: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.hard_abort_if = [str(item) for item in _as_list(self.hard_abort_if)]
        self.warning_if = [str(item) for item in _as_list(self.warning_if)]

    def to_dict(self) -> dict[str, Any]:
        return {"hard_abort_if": list(self.hard_abort_if), "warning_if": list(self.warning_if)}


@dataclass
class PromptConstraintProductionLimitedDecisionV1:
    schema_version: str = "prompt_constraint_production_limited_rollout_decision_v1"
    prd: str = "PRD-046.1.12"
    final_status: str = "blocked"
    decision: str = "blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_rollout_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.12")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.recommended_next_prd = _as_str(self.recommended_next_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "recommended_next_prd": self.recommended_next_prd,
        }


@dataclass
class PromptConstraintProductionLimitedRolloutPlanV1:
    schema_version: str = "prompt_constraint_production_limited_rollout_plan_v1"
    prd: str = "PRD-046.1.12"
    source_consolidation_prd: str = "PRD-046.1.11"
    source_decision: str = ""
    rollout_stage: str = "plan_only"
    production_execution_performed: bool = False
    baseline_defaults: dict[str, Any] = field(default_factory=dict)
    cohort_policy: PromptConstraintProductionLimitedCohortPolicyV1 = field(default_factory=PromptConstraintProductionLimitedCohortPolicyV1)
    preflight_gates: dict[str, Any] = field(default_factory=dict)
    operator_checklist: dict[str, Any] = field(default_factory=dict)
    monitoring_plan: dict[str, Any] = field(default_factory=dict)
    rollback_plan: dict[str, Any] = field(default_factory=dict)
    abort_criteria: dict[str, Any] = field(default_factory=dict)
    decision: str = "stay_supervised"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_rollout_plan_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.12")
        self.source_consolidation_prd = _as_str(self.source_consolidation_prd, "PRD-046.1.11")
        self.source_decision = _as_str(self.source_decision, "")
        self.rollout_stage = _as_str(self.rollout_stage, "plan_only")
        self.production_execution_performed = _as_bool(self.production_execution_performed, False)
        self.baseline_defaults = _safe_dict(self.baseline_defaults)
        if not isinstance(self.cohort_policy, PromptConstraintProductionLimitedCohortPolicyV1):
            self.cohort_policy = PromptConstraintProductionLimitedCohortPolicyV1(**_safe_dict(self.cohort_policy))
        self.preflight_gates = _safe_dict(self.preflight_gates)
        self.operator_checklist = _safe_dict(self.operator_checklist)
        self.monitoring_plan = _safe_dict(self.monitoring_plan)
        self.rollback_plan = _safe_dict(self.rollback_plan)
        self.abort_criteria = _safe_dict(self.abort_criteria)
        self.decision = _as_str(self.decision, "stay_supervised")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_consolidation_prd": self.source_consolidation_prd,
            "source_decision": self.source_decision,
            "rollout_stage": self.rollout_stage,
            "production_execution_performed": bool(self.production_execution_performed),
            "baseline_defaults": dict(self.baseline_defaults),
            "cohort_policy": self.cohort_policy.to_dict(),
            "preflight_gates": dict(self.preflight_gates),
            "operator_checklist": dict(self.operator_checklist),
            "monitoring_plan": dict(self.monitoring_plan),
            "rollback_plan": dict(self.rollback_plan),
            "abort_criteria": dict(self.abort_criteria),
            "decision": self.decision,
        }
