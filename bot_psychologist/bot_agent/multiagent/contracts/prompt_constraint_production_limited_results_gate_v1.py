"""Contracts for PRD-046.1.14 production-limited results/rollback/quality gate."""

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
class PromptConstraintProductionLimitedSourceEvidenceV1:
    source_execution_prd: str = "PRD-046.1.13"
    source_final_status: str = "blocked"
    source_decision: str = "stop"
    source_execution_window_count: int = 0
    source_target_user_count: int = 0
    source_production_limited_apply_count: int = 0

    def __post_init__(self) -> None:
        self.source_execution_prd = _as_str(self.source_execution_prd, "PRD-046.1.13")
        self.source_final_status = _as_str(self.source_final_status, "blocked")
        self.source_decision = _as_str(self.source_decision, "stop")
        self.source_execution_window_count = _as_int(self.source_execution_window_count, 0, minimum=0)
        self.source_target_user_count = _as_int(self.source_target_user_count, 0, minimum=0)
        self.source_production_limited_apply_count = _as_int(self.source_production_limited_apply_count, 0, minimum=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_execution_prd": self.source_execution_prd,
            "source_final_status": self.source_final_status,
            "source_decision": self.source_decision,
            "source_execution_window_count": int(self.source_execution_window_count),
            "source_target_user_count": int(self.source_target_user_count),
            "source_production_limited_apply_count": int(self.source_production_limited_apply_count),
        }


@dataclass
class PromptConstraintProductionLimitedQualitySummaryV1:
    cases_compared: int = 0
    production_limited_apply_count: int = 0
    candidate_weaker_than_baseline_count: int = 0
    safety_regression_count: int = 0
    kb_policy_regression_count: int = 0
    prompt_bloat_regression_count: int = 0
    constraint_conflict_regression_count: int = 0
    raw_kb_text_exposure_count: int = 0
    internal_only_exposure_count: int = 0
    not_for_direct_quote_violation_count: int = 0
    provider_called_by_execution_count: int = 0
    quality_gate_passed: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "cases_compared",
            "production_limited_apply_count",
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
        self.quality_gate_passed = _as_bool(self.quality_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases_compared": int(self.cases_compared),
            "production_limited_apply_count": int(self.production_limited_apply_count),
            "candidate_weaker_than_baseline_count": int(self.candidate_weaker_than_baseline_count),
            "safety_regression_count": int(self.safety_regression_count),
            "kb_policy_regression_count": int(self.kb_policy_regression_count),
            "prompt_bloat_regression_count": int(self.prompt_bloat_regression_count),
            "constraint_conflict_regression_count": int(self.constraint_conflict_regression_count),
            "raw_kb_text_exposure_count": int(self.raw_kb_text_exposure_count),
            "internal_only_exposure_count": int(self.internal_only_exposure_count),
            "not_for_direct_quote_violation_count": int(self.not_for_direct_quote_violation_count),
            "provider_called_by_execution_count": int(self.provider_called_by_execution_count),
            "quality_gate_passed": bool(self.quality_gate_passed),
        }


@dataclass
class PromptConstraintProductionLimitedRollbackSummaryV1:
    rollback_cases_total: int = 0
    rollback_cases_passed: int = 0
    rollback_failure_count: int = 0
    stale_apply_after_force_disabled_count: int = 0
    force_disabled_absolute_priority: bool = False
    allowlisted_target_apply_after_rollback: int = 0
    rollback_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.rollback_cases_total = _as_int(self.rollback_cases_total, 0, minimum=0)
        self.rollback_cases_passed = _as_int(self.rollback_cases_passed, 0, minimum=0)
        self.rollback_failure_count = _as_int(self.rollback_failure_count, 0, minimum=0)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0, minimum=0)
        self.force_disabled_absolute_priority = _as_bool(self.force_disabled_absolute_priority, False)
        self.allowlisted_target_apply_after_rollback = _as_int(self.allowlisted_target_apply_after_rollback, 0, minimum=0)
        self.rollback_gate_passed = _as_bool(self.rollback_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_cases_total": int(self.rollback_cases_total),
            "rollback_cases_passed": int(self.rollback_cases_passed),
            "rollback_failure_count": int(self.rollback_failure_count),
            "stale_apply_after_force_disabled_count": int(self.stale_apply_after_force_disabled_count),
            "force_disabled_absolute_priority": bool(self.force_disabled_absolute_priority),
            "allowlisted_target_apply_after_rollback": int(self.allowlisted_target_apply_after_rollback),
            "rollback_gate_passed": bool(self.rollback_gate_passed),
        }


@dataclass
class PromptConstraintProductionLimitedNormalUserSummaryV1:
    normal_user_cases_total: int = 0
    normal_user_apply_count: int = 0
    default_off_user_path_effect_count: int = 0
    normal_user_prompt_changed_by_pilot_count: int = 0
    normal_user_final_answer_changed_by_pilot_count: int = 0
    normal_user_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.normal_user_cases_total = _as_int(self.normal_user_cases_total, 0, minimum=0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0, minimum=0)
        self.default_off_user_path_effect_count = _as_int(self.default_off_user_path_effect_count, 0, minimum=0)
        self.normal_user_prompt_changed_by_pilot_count = _as_int(self.normal_user_prompt_changed_by_pilot_count, 0, minimum=0)
        self.normal_user_final_answer_changed_by_pilot_count = _as_int(self.normal_user_final_answer_changed_by_pilot_count, 0, minimum=0)
        self.normal_user_gate_passed = _as_bool(self.normal_user_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "normal_user_cases_total": int(self.normal_user_cases_total),
            "normal_user_apply_count": int(self.normal_user_apply_count),
            "default_off_user_path_effect_count": int(self.default_off_user_path_effect_count),
            "normal_user_prompt_changed_by_pilot_count": int(self.normal_user_prompt_changed_by_pilot_count),
            "normal_user_final_answer_changed_by_pilot_count": int(self.normal_user_final_answer_changed_by_pilot_count),
            "normal_user_gate_passed": bool(self.normal_user_gate_passed),
        }


@dataclass
class PromptConstraintProductionLimitedPostRunRiskRegisterV1:
    risks: list[dict[str, Any]] = field(default_factory=list)
    risk_register_has_blockers: bool = False
    blocking_risk_count: int = 0

    def __post_init__(self) -> None:
        self.risks = [_safe_dict(item) for item in _as_list(self.risks)]
        self.risk_register_has_blockers = _as_bool(self.risk_register_has_blockers, False)
        self.blocking_risk_count = _as_int(self.blocking_risk_count, 0, minimum=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risks": list(self.risks),
            "risk_register_has_blockers": bool(self.risk_register_has_blockers),
            "blocking_risk_count": int(self.blocking_risk_count),
        }


@dataclass
class PromptConstraintProductionLimitedResultsDecisionV1:
    schema_version: str = "prompt_constraint_production_limited_results_decision_v1"
    prd: str = "PRD-046.1.14"
    final_status: str = "blocked"
    decision: str = "stop"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_results_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.14")
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
class PromptConstraintProductionLimitedResultsGateV1:
    schema_version: str = "prompt_constraint_production_limited_results_gate_v1"
    prd: str = "PRD-046.1.14"
    source_execution_prd: str = "PRD-046.1.13"
    gate_mode: str = "post_run_results_only"
    new_execution_performed: bool = False
    source_evidence: PromptConstraintProductionLimitedSourceEvidenceV1 = field(default_factory=PromptConstraintProductionLimitedSourceEvidenceV1)
    quality_summary: PromptConstraintProductionLimitedQualitySummaryV1 = field(default_factory=PromptConstraintProductionLimitedQualitySummaryV1)
    rollback_summary: PromptConstraintProductionLimitedRollbackSummaryV1 = field(default_factory=PromptConstraintProductionLimitedRollbackSummaryV1)
    normal_user_summary: PromptConstraintProductionLimitedNormalUserSummaryV1 = field(default_factory=PromptConstraintProductionLimitedNormalUserSummaryV1)
    trace_sanitization_summary: dict[str, Any] = field(default_factory=dict)
    post_run_risk_register: PromptConstraintProductionLimitedPostRunRiskRegisterV1 = field(default_factory=PromptConstraintProductionLimitedPostRunRiskRegisterV1)
    decision: str = "stay_limited"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_production_limited_results_gate_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.14")
        self.source_execution_prd = _as_str(self.source_execution_prd, "PRD-046.1.13")
        self.gate_mode = _as_str(self.gate_mode, "post_run_results_only")
        self.new_execution_performed = _as_bool(self.new_execution_performed, False)
        if not isinstance(self.source_evidence, PromptConstraintProductionLimitedSourceEvidenceV1):
            self.source_evidence = PromptConstraintProductionLimitedSourceEvidenceV1(**_safe_dict(self.source_evidence))
        if not isinstance(self.quality_summary, PromptConstraintProductionLimitedQualitySummaryV1):
            self.quality_summary = PromptConstraintProductionLimitedQualitySummaryV1(**_safe_dict(self.quality_summary))
        if not isinstance(self.rollback_summary, PromptConstraintProductionLimitedRollbackSummaryV1):
            self.rollback_summary = PromptConstraintProductionLimitedRollbackSummaryV1(**_safe_dict(self.rollback_summary))
        if not isinstance(self.normal_user_summary, PromptConstraintProductionLimitedNormalUserSummaryV1):
            self.normal_user_summary = PromptConstraintProductionLimitedNormalUserSummaryV1(**_safe_dict(self.normal_user_summary))
        self.trace_sanitization_summary = _safe_dict(self.trace_sanitization_summary)
        if not isinstance(self.post_run_risk_register, PromptConstraintProductionLimitedPostRunRiskRegisterV1):
            self.post_run_risk_register = PromptConstraintProductionLimitedPostRunRiskRegisterV1(**_safe_dict(self.post_run_risk_register))
        self.decision = _as_str(self.decision, "stay_limited")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_execution_prd": self.source_execution_prd,
            "gate_mode": self.gate_mode,
            "new_execution_performed": bool(self.new_execution_performed),
            "source_evidence": self.source_evidence.to_dict(),
            "quality_summary": self.quality_summary.to_dict(),
            "rollback_summary": self.rollback_summary.to_dict(),
            "normal_user_summary": self.normal_user_summary.to_dict(),
            "trace_sanitization_summary": dict(self.trace_sanitization_summary),
            "post_run_risk_register": self.post_run_risk_register.to_dict(),
            "decision": self.decision,
        }
