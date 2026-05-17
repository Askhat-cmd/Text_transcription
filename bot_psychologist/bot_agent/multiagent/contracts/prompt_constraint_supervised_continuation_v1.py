"""Contracts for PRD-046.1.10 supervised continuation expanded eval cohort."""

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


def _as_float(value: Any, default: float = 0.0, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class PromptConstraintSupervisedContinuationCohortV1:
    max_size: int = 6
    actual_size: int = 0
    normal_users_included: bool = False
    user_ids: list[str] = field(default_factory=list)
    all_user_ids_allowlisted_or_test_prefix: bool = True

    def __post_init__(self) -> None:
        self.max_size = _as_int(self.max_size, 6, minimum=1)
        self.actual_size = _as_int(self.actual_size, 0, minimum=0)
        self.normal_users_included = _as_bool(self.normal_users_included, False)
        self.user_ids = [str(item) for item in _as_list(self.user_ids)]
        self.all_user_ids_allowlisted_or_test_prefix = _as_bool(self.all_user_ids_allowlisted_or_test_prefix, True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_size": int(self.max_size),
            "actual_size": int(self.actual_size),
            "normal_users_included": bool(self.normal_users_included),
            "user_ids": list(self.user_ids),
            "all_user_ids_allowlisted_or_test_prefix": bool(self.all_user_ids_allowlisted_or_test_prefix),
        }


@dataclass
class PromptConstraintSupervisedContinuationCaseV1:
    case_id: str = ""
    user_id: str = ""
    scenario: str = ""
    activation_mode: str = "disabled"
    apply_allowed: bool = False
    applied: bool = False
    downgrade_reason: str | None = None
    safety_gate_passed: bool = True
    kb_gate_passed: bool = True
    conflict_gate_passed: bool = True
    bloat_gate_passed: bool = True
    prompt_delta_chars: int = 0
    prompt_delta_ratio: float = 0.0
    raw_kb_text_exposed: bool = False
    internal_only_exposed: bool = False
    not_for_direct_quote_violated: bool = False
    provider_called: bool = False

    def __post_init__(self) -> None:
        self.case_id = _as_str(self.case_id, "")
        self.user_id = _as_str(self.user_id, "")
        self.scenario = _as_str(self.scenario, "")
        self.activation_mode = _as_str(self.activation_mode, "disabled")
        self.apply_allowed = _as_bool(self.apply_allowed, False)
        self.applied = _as_bool(self.applied, False)
        self.downgrade_reason = None if self.downgrade_reason is None else _as_str(self.downgrade_reason, "")
        self.safety_gate_passed = _as_bool(self.safety_gate_passed, True)
        self.kb_gate_passed = _as_bool(self.kb_gate_passed, True)
        self.conflict_gate_passed = _as_bool(self.conflict_gate_passed, True)
        self.bloat_gate_passed = _as_bool(self.bloat_gate_passed, True)
        self.prompt_delta_chars = _as_int(self.prompt_delta_chars, 0, minimum=0)
        self.prompt_delta_ratio = _as_float(self.prompt_delta_ratio, 0.0, minimum=0.0)
        self.raw_kb_text_exposed = _as_bool(self.raw_kb_text_exposed, False)
        self.internal_only_exposed = _as_bool(self.internal_only_exposed, False)
        self.not_for_direct_quote_violated = _as_bool(self.not_for_direct_quote_violated, False)
        self.provider_called = _as_bool(self.provider_called, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "user_id": self.user_id,
            "scenario": self.scenario,
            "activation_mode": self.activation_mode,
            "apply_allowed": bool(self.apply_allowed),
            "applied": bool(self.applied),
            "downgrade_reason": self.downgrade_reason,
            "safety_gate_passed": bool(self.safety_gate_passed),
            "kb_gate_passed": bool(self.kb_gate_passed),
            "conflict_gate_passed": bool(self.conflict_gate_passed),
            "bloat_gate_passed": bool(self.bloat_gate_passed),
            "prompt_delta_chars": int(self.prompt_delta_chars),
            "prompt_delta_ratio": float(self.prompt_delta_ratio),
            "raw_kb_text_exposed": bool(self.raw_kb_text_exposed),
            "internal_only_exposed": bool(self.internal_only_exposed),
            "not_for_direct_quote_violated": bool(self.not_for_direct_quote_violated),
            "provider_called": bool(self.provider_called),
        }


@dataclass
class PromptConstraintSupervisedContinuationComparisonV1:
    schema_version: str = "prompt_constraint_supervised_continuation_comparison_v1"
    prd: str = "PRD-046.1.10"
    cases_compared: int = 0
    test_apply_applied_count: int = 0
    candidate_weaker_than_baseline_count: int = 0
    safety_regression_count: int = 0
    kb_policy_regression_count: int = 0
    prompt_bloat_regression_count: int = 0
    constraint_conflict_regression_count: int = 0
    raw_kb_text_exposure_count: int = 0
    internal_only_exposure_count: int = 0
    not_for_direct_quote_violation_count: int = 0
    provider_called_by_continuation_count: int = 0

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_continuation_comparison_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.10")
        self.cases_compared = _as_int(self.cases_compared, 0, minimum=0)
        self.test_apply_applied_count = _as_int(self.test_apply_applied_count, 0, minimum=0)
        self.candidate_weaker_than_baseline_count = _as_int(self.candidate_weaker_than_baseline_count, 0, minimum=0)
        self.safety_regression_count = _as_int(self.safety_regression_count, 0, minimum=0)
        self.kb_policy_regression_count = _as_int(self.kb_policy_regression_count, 0, minimum=0)
        self.prompt_bloat_regression_count = _as_int(self.prompt_bloat_regression_count, 0, minimum=0)
        self.constraint_conflict_regression_count = _as_int(self.constraint_conflict_regression_count, 0, minimum=0)
        self.raw_kb_text_exposure_count = _as_int(self.raw_kb_text_exposure_count, 0, minimum=0)
        self.internal_only_exposure_count = _as_int(self.internal_only_exposure_count, 0, minimum=0)
        self.not_for_direct_quote_violation_count = _as_int(self.not_for_direct_quote_violation_count, 0, minimum=0)
        self.provider_called_by_continuation_count = _as_int(self.provider_called_by_continuation_count, 0, minimum=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "cases_compared": int(self.cases_compared),
            "test_apply_applied_count": int(self.test_apply_applied_count),
            "candidate_weaker_than_baseline_count": int(self.candidate_weaker_than_baseline_count),
            "safety_regression_count": int(self.safety_regression_count),
            "kb_policy_regression_count": int(self.kb_policy_regression_count),
            "prompt_bloat_regression_count": int(self.prompt_bloat_regression_count),
            "constraint_conflict_regression_count": int(self.constraint_conflict_regression_count),
            "raw_kb_text_exposure_count": int(self.raw_kb_text_exposure_count),
            "internal_only_exposure_count": int(self.internal_only_exposure_count),
            "not_for_direct_quote_violation_count": int(self.not_for_direct_quote_violation_count),
            "provider_called_by_continuation_count": int(self.provider_called_by_continuation_count),
        }


@dataclass
class PromptConstraintSupervisedContinuationRollbackV1:
    schema_version: str = "prompt_constraint_supervised_continuation_rollback_v1"
    prd: str = "PRD-046.1.10"
    rollback_cases_total: int = 0
    rollback_cases_passed: int = 0
    rollback_failure_count: int = 0
    stale_apply_after_force_disabled_count: int = 0
    force_disabled_absolute_priority: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_continuation_rollback_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.10")
        self.rollback_cases_total = _as_int(self.rollback_cases_total, 0, minimum=0)
        self.rollback_cases_passed = _as_int(self.rollback_cases_passed, 0, minimum=0)
        self.rollback_failure_count = _as_int(self.rollback_failure_count, 0, minimum=0)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0, minimum=0)
        self.force_disabled_absolute_priority = _as_bool(self.force_disabled_absolute_priority, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "rollback_cases_total": int(self.rollback_cases_total),
            "rollback_cases_passed": int(self.rollback_cases_passed),
            "rollback_failure_count": int(self.rollback_failure_count),
            "stale_apply_after_force_disabled_count": int(self.stale_apply_after_force_disabled_count),
            "force_disabled_absolute_priority": bool(self.force_disabled_absolute_priority),
        }


@dataclass
class PromptConstraintSupervisedContinuationDecisionV1:
    schema_version: str = "prompt_constraint_supervised_continuation_decision_v1"
    prd: str = "PRD-046.1.10"
    final_status: str = "blocked"
    decision: str = "stop"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_continuation_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.10")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "stop")
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
class PromptConstraintSupervisedContinuationRunV1:
    schema_version: str = "prompt_constraint_supervised_continuation_v1"
    prd: str = "PRD-046.1.10"
    source_execution_prd: str = "PRD-046.1.9"
    source_execution_decision: str = ""
    execution_mode: str = "controlled_harness_expanded_eval"
    cohort: PromptConstraintSupervisedContinuationCohortV1 = field(default_factory=PromptConstraintSupervisedContinuationCohortV1)
    scenario_coverage: dict[str, Any] = field(default_factory=dict)
    baseline_defaults_preserved: bool = True
    results: dict[str, Any] = field(default_factory=dict)
    decision: str = "stay_limited"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_continuation_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.10")
        self.source_execution_prd = _as_str(self.source_execution_prd, "PRD-046.1.9")
        self.source_execution_decision = _as_str(self.source_execution_decision, "")
        self.execution_mode = _as_str(self.execution_mode, "controlled_harness_expanded_eval")
        if not isinstance(self.cohort, PromptConstraintSupervisedContinuationCohortV1):
            self.cohort = PromptConstraintSupervisedContinuationCohortV1(**_safe_dict(self.cohort))
        self.scenario_coverage = _safe_dict(self.scenario_coverage)
        self.baseline_defaults_preserved = _as_bool(self.baseline_defaults_preserved, True)
        self.results = _safe_dict(self.results)
        self.decision = _as_str(self.decision, "stay_limited")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_execution_prd": self.source_execution_prd,
            "source_execution_decision": self.source_execution_decision,
            "execution_mode": self.execution_mode,
            "cohort": self.cohort.to_dict(),
            "scenario_coverage": dict(self.scenario_coverage),
            "baseline_defaults_preserved": bool(self.baseline_defaults_preserved),
            "results": dict(self.results),
            "decision": self.decision,
        }
