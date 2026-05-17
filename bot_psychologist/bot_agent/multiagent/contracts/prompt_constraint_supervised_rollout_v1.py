"""Contracts for PRD-046.1.8 supervised prompt-constraint rollout planning."""

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


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class PromptConstraintRolloutCohortV1:
    allowlisted_user_ids_only: bool = True
    test_user_prefix_only: bool = True
    max_cohort_size: int = 3
    normal_users_allowed: bool = False
    explicit_allowlisted_user_ids: list[str] = field(default_factory=list)
    required_test_user_prefix: str = "pilot_"

    def __post_init__(self) -> None:
        self.allowlisted_user_ids_only = _as_bool(self.allowlisted_user_ids_only, True)
        self.test_user_prefix_only = _as_bool(self.test_user_prefix_only, True)
        self.max_cohort_size = _as_int(self.max_cohort_size, 3, minimum=1)
        self.normal_users_allowed = _as_bool(self.normal_users_allowed, False)
        self.explicit_allowlisted_user_ids = _as_list(self.explicit_allowlisted_user_ids)
        self.required_test_user_prefix = _as_str(self.required_test_user_prefix, "pilot_")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowlisted_user_ids_only": bool(self.allowlisted_user_ids_only),
            "test_user_prefix_only": bool(self.test_user_prefix_only),
            "max_cohort_size": int(self.max_cohort_size),
            "normal_users_allowed": bool(self.normal_users_allowed),
            "explicit_allowlisted_user_ids": list(self.explicit_allowlisted_user_ids),
            "required_test_user_prefix": self.required_test_user_prefix,
        }


@dataclass
class PromptConstraintRolloutGateV1:
    gate_id: str = ""
    required: bool = True
    passed: bool = False
    details: str = ""

    def __post_init__(self) -> None:
        self.gate_id = _as_str(self.gate_id, "")
        self.required = _as_bool(self.required, True)
        self.passed = _as_bool(self.passed, False)
        self.details = _as_str(self.details, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "required": bool(self.required),
            "passed": bool(self.passed),
            "details": self.details,
        }


@dataclass
class PromptConstraintRolloutAbortCriteriaV1:
    schema_version: str = "prompt_constraint_supervised_rollout_abort_criteria_v1"
    hard_abort_conditions: list[str] = field(default_factory=list)
    warning_conditions: list[str] = field(default_factory=list)
    rollback_steps: list[str] = field(default_factory=list)
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(
            self.schema_version,
            "prompt_constraint_supervised_rollout_abort_criteria_v1",
        )
        self.hard_abort_conditions = _as_list(self.hard_abort_conditions)
        self.warning_conditions = _as_list(self.warning_conditions)
        self.rollback_steps = _as_list(self.rollback_steps)
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "hard_abort_conditions": list(self.hard_abort_conditions),
            "warning_conditions": list(self.warning_conditions),
            "rollback_steps": list(self.rollback_steps),
            "ready": bool(self.ready),
        }


@dataclass
class PromptConstraintRolloutMetricV1:
    metric_id: str = ""
    source: str = ""
    target: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        self.metric_id = _as_str(self.metric_id, "")
        self.source = _as_str(self.source, "")
        self.target = _as_str(self.target, "")
        self.required = _as_bool(self.required, True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "source": self.source,
            "target": self.target,
            "required": bool(self.required),
        }


@dataclass
class PromptConstraintRolloutDecisionV1:
    schema_version: str = "prompt_constraint_supervised_rollout_decision_v1"
    final_status: str = "blocked"
    decision: str = "execution_blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(
            self.schema_version,
            "prompt_constraint_supervised_rollout_decision_v1",
        )
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "execution_blocked")
        self.blockers = _as_list(self.blockers)
        self.warnings = _as_list(self.warnings)
        self.recommended_next_prd = _as_str(self.recommended_next_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "recommended_next_prd": self.recommended_next_prd,
        }


@dataclass
class PromptConstraintSupervisedRolloutPlanV1:
    schema_version: str = "prompt_constraint_supervised_rollout_plan_v1"
    prd: str = "PRD-046.1.8"
    baseline_defaults: dict[str, Any] = field(default_factory=dict)
    rollout_stage: str = "plan_only"
    allowed_scope: PromptConstraintRolloutCohortV1 = field(default_factory=PromptConstraintRolloutCohortV1)
    required_preflight_gates: list[PromptConstraintRolloutGateV1] = field(default_factory=list)
    runtime_observation_requirements: list[PromptConstraintRolloutMetricV1] = field(default_factory=list)
    abort_criteria: PromptConstraintRolloutAbortCriteriaV1 = field(default_factory=PromptConstraintRolloutAbortCriteriaV1)
    rollback_steps: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    next_decision_options: list[str] = field(
        default_factory=lambda: [
            "execution_blocked",
            "ready_for_supervised_execution_prd",
            "hotfix_required",
        ]
    )

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_rollout_plan_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.8")
        self.baseline_defaults = _safe_dict(self.baseline_defaults)
        self.rollout_stage = _as_str(self.rollout_stage, "plan_only")
        if not isinstance(self.allowed_scope, PromptConstraintRolloutCohortV1):
            self.allowed_scope = PromptConstraintRolloutCohortV1(**_safe_dict(self.allowed_scope))
        self.required_preflight_gates = [
            item if isinstance(item, PromptConstraintRolloutGateV1) else PromptConstraintRolloutGateV1(**_safe_dict(item))
            for item in self.required_preflight_gates
        ]
        self.runtime_observation_requirements = [
            item if isinstance(item, PromptConstraintRolloutMetricV1) else PromptConstraintRolloutMetricV1(**_safe_dict(item))
            for item in self.runtime_observation_requirements
        ]
        if not isinstance(self.abort_criteria, PromptConstraintRolloutAbortCriteriaV1):
            self.abort_criteria = PromptConstraintRolloutAbortCriteriaV1(**_safe_dict(self.abort_criteria))
        self.rollback_steps = _as_list(self.rollback_steps)
        self.success_criteria = _as_list(self.success_criteria)
        self.next_decision_options = _as_list(self.next_decision_options)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "baseline_defaults": dict(self.baseline_defaults),
            "rollout_stage": self.rollout_stage,
            "allowed_scope": self.allowed_scope.to_dict(),
            "required_preflight_gates": [item.to_dict() for item in self.required_preflight_gates],
            "runtime_observation_requirements": [item.to_dict() for item in self.runtime_observation_requirements],
            "abort_criteria": self.abort_criteria.to_dict(),
            "rollback_steps": list(self.rollback_steps),
            "success_criteria": list(self.success_criteria),
            "next_decision_options": list(self.next_decision_options),
        }
