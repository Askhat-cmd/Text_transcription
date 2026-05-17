"""Contracts for PRD-046.1.11 supervised results consolidation gate."""

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
class PromptConstraintSupervisedCycleEvidenceV1:
    prd: str = ""
    final_status: str = "blocked"
    decision: str = "stop"
    cohort_size: int = 0
    test_apply_applied_count: int = 0
    cases_compared: int = 0

    def __post_init__(self) -> None:
        self.prd = _as_str(self.prd, "")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "stop")
        self.cohort_size = _as_int(self.cohort_size, 0, minimum=0)
        self.test_apply_applied_count = _as_int(self.test_apply_applied_count, 0, minimum=0)
        self.cases_compared = _as_int(self.cases_compared, 0, minimum=0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prd": self.prd,
            "final_status": self.final_status,
            "decision": self.decision,
            "cohort_size": int(self.cohort_size),
            "test_apply_applied_count": int(self.test_apply_applied_count),
            "cases_compared": int(self.cases_compared),
        }


@dataclass
class PromptConstraintSupervisedAggregateMetricsV1:
    schema_version: str = "prompt_constraint_supervised_consolidation_aggregate_metrics_v1"
    prd: str = "PRD-046.1.11"
    cycles_total: int = 0
    cycles_passed: int = 0
    total_test_apply_applied_count: int = 0
    total_cases_compared: int = 0
    max_cohort_size_seen: int = 0
    normal_user_apply_total: int = 0
    default_off_user_path_effect_total: int = 0
    rollback_failure_total: int = 0
    stale_apply_after_force_disabled_total: int = 0
    candidate_weaker_than_baseline_total: int = 0
    safety_regression_total: int = 0
    kb_policy_regression_total: int = 0
    prompt_bloat_regression_total: int = 0
    constraint_conflict_regression_total: int = 0
    raw_kb_text_exposure_total: int = 0
    internal_only_exposure_total: int = 0
    not_for_direct_quote_violation_total: int = 0
    provider_called_total: int = 0
    production_mutation_detected_any: bool = False
    artifact_encoding_hygiene_all_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_consolidation_aggregate_metrics_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.11")
        for field_name in (
            "cycles_total",
            "cycles_passed",
            "total_test_apply_applied_count",
            "total_cases_compared",
            "max_cohort_size_seen",
            "normal_user_apply_total",
            "default_off_user_path_effect_total",
            "rollback_failure_total",
            "stale_apply_after_force_disabled_total",
            "candidate_weaker_than_baseline_total",
            "safety_regression_total",
            "kb_policy_regression_total",
            "prompt_bloat_regression_total",
            "constraint_conflict_regression_total",
            "raw_kb_text_exposure_total",
            "internal_only_exposure_total",
            "not_for_direct_quote_violation_total",
            "provider_called_total",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0, minimum=0))
        self.production_mutation_detected_any = _as_bool(self.production_mutation_detected_any, False)
        self.artifact_encoding_hygiene_all_passed = _as_bool(self.artifact_encoding_hygiene_all_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "cycles_total": int(self.cycles_total),
            "cycles_passed": int(self.cycles_passed),
            "total_test_apply_applied_count": int(self.total_test_apply_applied_count),
            "total_cases_compared": int(self.total_cases_compared),
            "max_cohort_size_seen": int(self.max_cohort_size_seen),
            "normal_user_apply_total": int(self.normal_user_apply_total),
            "default_off_user_path_effect_total": int(self.default_off_user_path_effect_total),
            "rollback_failure_total": int(self.rollback_failure_total),
            "stale_apply_after_force_disabled_total": int(self.stale_apply_after_force_disabled_total),
            "candidate_weaker_than_baseline_total": int(self.candidate_weaker_than_baseline_total),
            "safety_regression_total": int(self.safety_regression_total),
            "kb_policy_regression_total": int(self.kb_policy_regression_total),
            "prompt_bloat_regression_total": int(self.prompt_bloat_regression_total),
            "constraint_conflict_regression_total": int(self.constraint_conflict_regression_total),
            "raw_kb_text_exposure_total": int(self.raw_kb_text_exposure_total),
            "internal_only_exposure_total": int(self.internal_only_exposure_total),
            "not_for_direct_quote_violation_total": int(self.not_for_direct_quote_violation_total),
            "provider_called_total": int(self.provider_called_total),
            "production_mutation_detected_any": bool(self.production_mutation_detected_any),
            "artifact_encoding_hygiene_all_passed": bool(self.artifact_encoding_hygiene_all_passed),
        }


@dataclass
class PromptConstraintSupervisedRiskRegisterV1:
    schema_version: str = "prompt_constraint_supervised_consolidation_risk_register_v1"
    prd: str = "PRD-046.1.11"
    risks: list[dict[str, Any]] = field(default_factory=list)
    blocking_risk_count: int = 0
    risk_register_has_blockers: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_consolidation_risk_register_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.11")
        self.risks = [dict(item) for item in _as_list(self.risks) if isinstance(item, dict)]
        self.blocking_risk_count = _as_int(self.blocking_risk_count, 0, minimum=0)
        self.risk_register_has_blockers = _as_bool(self.risk_register_has_blockers, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "risks": list(self.risks),
            "blocking_risk_count": int(self.blocking_risk_count),
            "risk_register_has_blockers": bool(self.risk_register_has_blockers),
        }


@dataclass
class PromptConstraintRolloutDecisionGateV1:
    schema_version: str = "prompt_constraint_supervised_consolidation_rollout_decision_gate_v1"
    prd: str = "PRD-046.1.11"
    final_status: str = "blocked"
    decision: str = "stop"
    source_cycles_passed: bool = False
    aggregate_metrics_passed: bool = False
    reproducibility_passed: bool = False
    risk_register_has_blockers: bool = True
    normal_user_apply_total: int = 0
    rollback_failure_total: int = 0
    safety_regression_total: int = 0
    kb_policy_regression_total: int = 0
    raw_kb_text_exposure_total: int = 0
    provider_called_total: int = 0
    production_mutation_detected_any: bool = False
    recommended_next_prd: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_consolidation_rollout_decision_gate_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.11")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "stop")
        self.source_cycles_passed = _as_bool(self.source_cycles_passed, False)
        self.aggregate_metrics_passed = _as_bool(self.aggregate_metrics_passed, False)
        self.reproducibility_passed = _as_bool(self.reproducibility_passed, False)
        self.risk_register_has_blockers = _as_bool(self.risk_register_has_blockers, True)
        self.normal_user_apply_total = _as_int(self.normal_user_apply_total, 0, minimum=0)
        self.rollback_failure_total = _as_int(self.rollback_failure_total, 0, minimum=0)
        self.safety_regression_total = _as_int(self.safety_regression_total, 0, minimum=0)
        self.kb_policy_regression_total = _as_int(self.kb_policy_regression_total, 0, minimum=0)
        self.raw_kb_text_exposure_total = _as_int(self.raw_kb_text_exposure_total, 0, minimum=0)
        self.provider_called_total = _as_int(self.provider_called_total, 0, minimum=0)
        self.production_mutation_detected_any = _as_bool(self.production_mutation_detected_any, False)
        self.recommended_next_prd = _as_str(self.recommended_next_prd, "")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "final_status": self.final_status,
            "decision": self.decision,
            "source_cycles_passed": bool(self.source_cycles_passed),
            "aggregate_metrics_passed": bool(self.aggregate_metrics_passed),
            "reproducibility_passed": bool(self.reproducibility_passed),
            "risk_register_has_blockers": bool(self.risk_register_has_blockers),
            "normal_user_apply_total": int(self.normal_user_apply_total),
            "rollback_failure_total": int(self.rollback_failure_total),
            "safety_regression_total": int(self.safety_regression_total),
            "kb_policy_regression_total": int(self.kb_policy_regression_total),
            "raw_kb_text_exposure_total": int(self.raw_kb_text_exposure_total),
            "provider_called_total": int(self.provider_called_total),
            "production_mutation_detected_any": bool(self.production_mutation_detected_any),
            "recommended_next_prd": self.recommended_next_prd,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass
class PromptConstraintRolloutDecisionV1:
    schema_version: str = "prompt_constraint_supervised_consolidation_decision_v1"
    prd: str = "PRD-046.1.11"
    final_status: str = "blocked"
    decision: str = "stop"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_consolidation_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.11")
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
class PromptConstraintSupervisedConsolidationRunV1:
    schema_version: str = "prompt_constraint_supervised_consolidation_v1"
    prd: str = "PRD-046.1.11"
    source_cycles: list[PromptConstraintSupervisedCycleEvidenceV1] = field(default_factory=list)
    aggregate_metrics: dict[str, Any] = field(default_factory=dict)
    reproducibility: dict[str, Any] = field(default_factory=dict)
    risk_register: dict[str, Any] = field(default_factory=dict)
    decision_gate: dict[str, Any] = field(default_factory=dict)
    decision: str = "stay_supervised"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_supervised_consolidation_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.11")
        normalized: list[PromptConstraintSupervisedCycleEvidenceV1] = []
        for item in _as_list(self.source_cycles):
            if isinstance(item, PromptConstraintSupervisedCycleEvidenceV1):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(PromptConstraintSupervisedCycleEvidenceV1(**item))
        self.source_cycles = normalized
        self.aggregate_metrics = _safe_dict(self.aggregate_metrics)
        self.reproducibility = _safe_dict(self.reproducibility)
        self.risk_register = _safe_dict(self.risk_register)
        self.decision_gate = _safe_dict(self.decision_gate)
        self.decision = _as_str(self.decision, "stay_supervised")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_cycles": [item.to_dict() for item in self.source_cycles],
            "aggregate_metrics": dict(self.aggregate_metrics),
            "reproducibility": dict(self.reproducibility),
            "risk_register": dict(self.risk_register),
            "decision_gate": dict(self.decision_gate),
            "decision": self.decision,
        }
