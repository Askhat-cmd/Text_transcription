"""Contracts for PRD-046.1.13 production-limited execution gate."""

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
class PromptConstraintProductionLimitedExecutionTargetV1:
    user_id: str = "prod_limited_operator_001"
    source: str = "synthetic_operator"
    real_user_count: int = 0
    synthetic_operator_user_count: int = 1
    allowlisted: bool = True

    def __post_init__(self) -> None:
        self.user_id = _as_str(self.user_id, "prod_limited_operator_001")
        self.source = _as_str(self.source, "synthetic_operator")
        self.real_user_count = _as_int(self.real_user_count, 0, minimum=0)
        self.synthetic_operator_user_count = _as_int(self.synthetic_operator_user_count, 1, minimum=0)
        self.allowlisted = _as_bool(self.allowlisted, True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "source": self.source,
            "real_user_count": int(self.real_user_count),
            "synthetic_operator_user_count": int(self.synthetic_operator_user_count),
            "allowlisted": bool(self.allowlisted),
        }


@dataclass
class PromptConstraintProductionLimitedPreflightResultV1:
    source_plan_gate_passed: bool = False
    operator_checklist_complete: bool = False
    monitoring_plan_ready: bool = False
    rollback_plan_ready: bool = False
    abort_criteria_ready: bool = False
    allowlist_ready: bool = False
    target_user_count_allowed: bool = False
    normal_user_controls_ready: bool = False
    config_defaults_conservative: bool = False
    force_disabled_available: bool = False
    preflight_passed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "source_plan_gate_passed",
            "operator_checklist_complete",
            "monitoring_plan_ready",
            "rollback_plan_ready",
            "abort_criteria_ready",
            "allowlist_ready",
            "target_user_count_allowed",
            "normal_user_controls_ready",
            "config_defaults_conservative",
            "force_disabled_available",
            "preflight_passed",
        ):
            setattr(self, field_name, _as_bool(getattr(self, field_name), False))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_plan_gate_passed": bool(self.source_plan_gate_passed),
            "operator_checklist_complete": bool(self.operator_checklist_complete),
            "monitoring_plan_ready": bool(self.monitoring_plan_ready),
            "rollback_plan_ready": bool(self.rollback_plan_ready),
            "abort_criteria_ready": bool(self.abort_criteria_ready),
            "allowlist_ready": bool(self.allowlist_ready),
            "target_user_count_allowed": bool(self.target_user_count_allowed),
            "normal_user_controls_ready": bool(self.normal_user_controls_ready),
            "config_defaults_conservative": bool(self.config_defaults_conservative),
            "force_disabled_available": bool(self.force_disabled_available),
            "preflight_passed": bool(self.preflight_passed),
        }


@dataclass
class PromptConstraintProductionLimitedTraceSampleV1:
    case_id: str = ""
    user_id_kind: str = "target"
    scenario: str = "baseline_default_off"
    activation_mode: str = "disabled"
    applied: bool = False
    apply_allowed: bool = False
    safety_gate_passed: bool = True
    kb_gate_passed: bool = True
    conflict_gate_passed: bool = True
    bloat_gate_passed: bool = True
    prompt_delta_chars: int = 0
    prompt_delta_ratio: float = 0.0
    raw_prompt_saved: bool = False
    raw_kb_text_exposed: bool = False
    private_user_text_saved: bool = False
    provider_called: bool = False

    def __post_init__(self) -> None:
        self.case_id = _as_str(self.case_id, "")
        self.user_id_kind = _as_str(self.user_id_kind, "target")
        self.scenario = _as_str(self.scenario, "baseline_default_off")
        self.activation_mode = _as_str(self.activation_mode, "disabled")
        self.applied = _as_bool(self.applied, False)
        self.apply_allowed = _as_bool(self.apply_allowed, False)
        self.safety_gate_passed = _as_bool(self.safety_gate_passed, True)
        self.kb_gate_passed = _as_bool(self.kb_gate_passed, True)
        self.conflict_gate_passed = _as_bool(self.conflict_gate_passed, True)
        self.bloat_gate_passed = _as_bool(self.bloat_gate_passed, True)
        self.prompt_delta_chars = _as_int(self.prompt_delta_chars, 0, minimum=0)
        self.prompt_delta_ratio = _as_float(self.prompt_delta_ratio, 0.0, minimum=0.0)
        self.raw_prompt_saved = _as_bool(self.raw_prompt_saved, False)
        self.raw_kb_text_exposed = _as_bool(self.raw_kb_text_exposed, False)
        self.private_user_text_saved = _as_bool(self.private_user_text_saved, False)
        self.provider_called = _as_bool(self.provider_called, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "user_id_kind": self.user_id_kind,
            "scenario": self.scenario,
            "activation_mode": self.activation_mode,
            "applied": bool(self.applied),
            "apply_allowed": bool(self.apply_allowed),
            "safety_gate_passed": bool(self.safety_gate_passed),
            "kb_gate_passed": bool(self.kb_gate_passed),
            "conflict_gate_passed": bool(self.conflict_gate_passed),
            "bloat_gate_passed": bool(self.bloat_gate_passed),
            "prompt_delta_chars": int(self.prompt_delta_chars),
            "prompt_delta_ratio": float(self.prompt_delta_ratio),
            "raw_prompt_saved": bool(self.raw_prompt_saved),
            "raw_kb_text_exposed": bool(self.raw_kb_text_exposed),
            "private_user_text_saved": bool(self.private_user_text_saved),
            "provider_called": bool(self.provider_called),
        }


@dataclass
class PromptConstraintProductionLimitedMonitoringMetricsV1:
    schema_version: str = "prompt_constraint_production_limited_monitoring_metrics_v1"
    prd: str = "PRD-046.1.13"
    source_plan_gate_passed: bool = False
    execution_window_count: int = 0
    target_user_count: int = 0
    target_user_limit_respected: bool = False
    production_limited_apply_count: int = 0
    normal_user_apply_count: int = 0
    default_off_user_path_effect_count: int = 0
    rollback_failure_count: int = 0
    stale_apply_after_force_disabled_count: int = 0
    candidate_weaker_than_baseline_count: int = 0
    safety_regression_count: int = 0
    kb_policy_regression_count: int = 0
    prompt_bloat_regression_count: int = 0
    constraint_conflict_regression_count: int = 0
    raw_kb_text_exposure_count: int = 0
    internal_only_exposure_count: int = 0
    not_for_direct_quote_violation_count: int = 0
    provider_called_by_execution_count: int = 0
    trace_sanitization_failed: bool = False
    production_mutation_detected: bool = False
    artifact_encoding_hygiene_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_monitoring_metrics_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.13")
        self.source_plan_gate_passed = _as_bool(self.source_plan_gate_passed, False)
        self.target_user_limit_respected = _as_bool(self.target_user_limit_respected, False)
        self.trace_sanitization_failed = _as_bool(self.trace_sanitization_failed, False)
        self.production_mutation_detected = _as_bool(self.production_mutation_detected, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        for field_name in (
            "execution_window_count",
            "target_user_count",
            "production_limited_apply_count",
            "normal_user_apply_count",
            "default_off_user_path_effect_count",
            "rollback_failure_count",
            "stale_apply_after_force_disabled_count",
            "candidate_weaker_than_baseline_count",
            "safety_regression_count",
            "kb_policy_regression_count",
            "prompt_bloat_regression_count",
            "constraint_conflict_regression_count",
            "raw_kb_text_exposure_count",
            "internal_only_exposure_count",
            "not_for_direct_quote_violation_count",
            "provider_called_by_execution_count",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0, minimum=0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_plan_gate_passed": bool(self.source_plan_gate_passed),
            "execution_window_count": int(self.execution_window_count),
            "target_user_count": int(self.target_user_count),
            "target_user_limit_respected": bool(self.target_user_limit_respected),
            "production_limited_apply_count": int(self.production_limited_apply_count),
            "normal_user_apply_count": int(self.normal_user_apply_count),
            "default_off_user_path_effect_count": int(self.default_off_user_path_effect_count),
            "rollback_failure_count": int(self.rollback_failure_count),
            "stale_apply_after_force_disabled_count": int(self.stale_apply_after_force_disabled_count),
            "candidate_weaker_than_baseline_count": int(self.candidate_weaker_than_baseline_count),
            "safety_regression_count": int(self.safety_regression_count),
            "kb_policy_regression_count": int(self.kb_policy_regression_count),
            "prompt_bloat_regression_count": int(self.prompt_bloat_regression_count),
            "constraint_conflict_regression_count": int(self.constraint_conflict_regression_count),
            "raw_kb_text_exposure_count": int(self.raw_kb_text_exposure_count),
            "internal_only_exposure_count": int(self.internal_only_exposure_count),
            "not_for_direct_quote_violation_count": int(self.not_for_direct_quote_violation_count),
            "provider_called_by_execution_count": int(self.provider_called_by_execution_count),
            "trace_sanitization_failed": bool(self.trace_sanitization_failed),
            "production_mutation_detected": bool(self.production_mutation_detected),
            "artifact_encoding_hygiene_passed": bool(self.artifact_encoding_hygiene_passed),
        }


@dataclass
class PromptConstraintProductionLimitedRollbackProofV1:
    schema_version: str = "prompt_constraint_production_limited_rollback_proof_v1"
    prd: str = "PRD-046.1.13"
    rollback_cases_total: int = 0
    rollback_cases_passed: int = 0
    rollback_failure_count: int = 0
    stale_apply_after_force_disabled_count: int = 0
    force_disabled_absolute_priority: bool = False
    allowlisted_target_apply_after_rollback: int = 0

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_rollback_proof_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.13")
        self.rollback_cases_total = _as_int(self.rollback_cases_total, 0, minimum=0)
        self.rollback_cases_passed = _as_int(self.rollback_cases_passed, 0, minimum=0)
        self.rollback_failure_count = _as_int(self.rollback_failure_count, 0, minimum=0)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0, minimum=0)
        self.force_disabled_absolute_priority = _as_bool(self.force_disabled_absolute_priority, False)
        self.allowlisted_target_apply_after_rollback = _as_int(self.allowlisted_target_apply_after_rollback, 0, minimum=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "rollback_cases_total": int(self.rollback_cases_total),
            "rollback_cases_passed": int(self.rollback_cases_passed),
            "rollback_failure_count": int(self.rollback_failure_count),
            "stale_apply_after_force_disabled_count": int(self.stale_apply_after_force_disabled_count),
            "force_disabled_absolute_priority": bool(self.force_disabled_absolute_priority),
            "allowlisted_target_apply_after_rollback": int(self.allowlisted_target_apply_after_rollback),
        }


@dataclass
class PromptConstraintProductionLimitedDecisionV1:
    schema_version: str = "prompt_constraint_production_limited_execution_decision_v1"
    prd: str = "PRD-046.1.13"
    final_status: str = "blocked"
    decision: str = "stop"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_execution_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.13")
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
class PromptConstraintProductionLimitedExecutionRunV1:
    schema_version: str = "prompt_constraint_production_limited_execution_v1"
    prd: str = "PRD-046.1.13"
    source_plan_prd: str = "PRD-046.1.12"
    execution_mode: str = "production_limited_controlled_window"
    execution_window: dict[str, Any] = field(default_factory=dict)
    target: PromptConstraintProductionLimitedExecutionTargetV1 = field(default_factory=PromptConstraintProductionLimitedExecutionTargetV1)
    baseline_defaults_preserved: bool = True
    results: dict[str, Any] = field(default_factory=dict)
    decision: str = "stay_limited"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_execution_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.13")
        self.source_plan_prd = _as_str(self.source_plan_prd, "PRD-046.1.12")
        self.execution_mode = _as_str(self.execution_mode, "production_limited_controlled_window")
        self.execution_window = _safe_dict(self.execution_window)
        if not isinstance(self.target, PromptConstraintProductionLimitedExecutionTargetV1):
            self.target = PromptConstraintProductionLimitedExecutionTargetV1(**_safe_dict(self.target))
        self.baseline_defaults_preserved = _as_bool(self.baseline_defaults_preserved, True)
        self.results = _safe_dict(self.results)
        self.decision = _as_str(self.decision, "stay_limited")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_plan_prd": self.source_plan_prd,
            "execution_mode": self.execution_mode,
            "execution_window": dict(self.execution_window),
            "target": self.target.to_dict(),
            "baseline_defaults_preserved": bool(self.baseline_defaults_preserved),
            "results": dict(self.results),
            "decision": self.decision,
        }
