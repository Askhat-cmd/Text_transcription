"""Contracts for PRD-046.1.26 limited smoke consolidation gate."""

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


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class LimitedSmokeConsolidationStatusV1:
    final_status: str = "blocked"
    decision: str = "blocker_requires_hotfix"
    source_chain_complete: bool = False
    source_chain_order_valid: bool = False
    missing_required_artifacts_count: int = 0
    source_decision_mismatch_count: int = 0
    provider_cycles_total: int = 0
    provider_cycles_passed: int = 0
    provider_scenarios_total: int = 0
    provider_calls_total: int = 0
    provider_budget_violations: int = 0
    normal_user_controls_total: int = 0
    normal_user_apply_count_total: int = 0
    normal_user_provider_calls_total: int = 0
    rollback_failures_total: int = 0
    raw_kb_quote_exposure_total: int = 0
    internal_only_raw_content_exposure_total: int = 0
    raw_provider_payload_in_artifacts: bool = False
    secret_like_values_count: int = 0
    botdb_stability_gate: str = "failed"
    quality_micro_shift_gate: str = "failed"
    no_mutation_gate: str = "failed"
    artifact_encoding_hygiene_passed: bool = False
    controlled_cohort_expansion_readiness_ready: bool = False
    future_cleanup_stabilization_requirement_created: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocker_requires_hotfix")
        self.source_chain_complete = _as_bool(self.source_chain_complete, False)
        self.source_chain_order_valid = _as_bool(self.source_chain_order_valid, False)
        self.missing_required_artifacts_count = _as_int(self.missing_required_artifacts_count, 0)
        self.source_decision_mismatch_count = _as_int(self.source_decision_mismatch_count, 0)
        self.provider_cycles_total = _as_int(self.provider_cycles_total, 0)
        self.provider_cycles_passed = _as_int(self.provider_cycles_passed, 0)
        self.provider_scenarios_total = _as_int(self.provider_scenarios_total, 0)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.provider_budget_violations = _as_int(self.provider_budget_violations, 0)
        self.normal_user_controls_total = _as_int(self.normal_user_controls_total, 0)
        self.normal_user_apply_count_total = _as_int(self.normal_user_apply_count_total, 0)
        self.normal_user_provider_calls_total = _as_int(self.normal_user_provider_calls_total, 0)
        self.rollback_failures_total = _as_int(self.rollback_failures_total, 0)
        self.raw_kb_quote_exposure_total = _as_int(self.raw_kb_quote_exposure_total, 0)
        self.internal_only_raw_content_exposure_total = _as_int(self.internal_only_raw_content_exposure_total, 0)
        self.raw_provider_payload_in_artifacts = _as_bool(self.raw_provider_payload_in_artifacts, False)
        self.secret_like_values_count = _as_int(self.secret_like_values_count, 0)
        self.botdb_stability_gate = _as_str(self.botdb_stability_gate, "failed")
        self.quality_micro_shift_gate = _as_str(self.quality_micro_shift_gate, "failed")
        self.no_mutation_gate = _as_str(self.no_mutation_gate, "failed")
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.controlled_cohort_expansion_readiness_ready = _as_bool(self.controlled_cohort_expansion_readiness_ready, False)
        self.future_cleanup_stabilization_requirement_created = _as_bool(
            self.future_cleanup_stabilization_requirement_created,
            False,
        )
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.next_recommended_prd = _as_str(self.next_recommended_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_chain_complete": self.source_chain_complete,
            "source_chain_order_valid": self.source_chain_order_valid,
            "missing_required_artifacts_count": self.missing_required_artifacts_count,
            "source_decision_mismatch_count": self.source_decision_mismatch_count,
            "provider_cycles_total": self.provider_cycles_total,
            "provider_cycles_passed": self.provider_cycles_passed,
            "provider_scenarios_total": self.provider_scenarios_total,
            "provider_calls_total": self.provider_calls_total,
            "provider_budget_violations": self.provider_budget_violations,
            "normal_user_controls_total": self.normal_user_controls_total,
            "normal_user_apply_count_total": self.normal_user_apply_count_total,
            "normal_user_provider_calls_total": self.normal_user_provider_calls_total,
            "rollback_failures_total": self.rollback_failures_total,
            "raw_kb_quote_exposure_total": self.raw_kb_quote_exposure_total,
            "internal_only_raw_content_exposure_total": self.internal_only_raw_content_exposure_total,
            "raw_provider_payload_in_artifacts": self.raw_provider_payload_in_artifacts,
            "secret_like_values_count": self.secret_like_values_count,
            "botdb_stability_gate": self.botdb_stability_gate,
            "quality_micro_shift_gate": self.quality_micro_shift_gate,
            "no_mutation_gate": self.no_mutation_gate,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "controlled_cohort_expansion_readiness_ready": self.controlled_cohort_expansion_readiness_ready,
            "future_cleanup_stabilization_requirement_created": self.future_cleanup_stabilization_requirement_created,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "next_recommended_prd": self.next_recommended_prd,
        }


@dataclass
class LimitedSmokeConsolidationDecisionV1:
    schema_version: str = "diagnostic_center_limited_smoke_consolidation_decision_v1"
    prd_id: str = "PRD-046.1.26"
    final_status: str = "blocked"
    decision: str = "blocker_requires_hotfix"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_smoke_consolidation_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.26")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocker_requires_hotfix")
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
class LimitedSmokeConsolidationBundleV1:
    source_gate: dict[str, Any] = field(default_factory=dict)
    cumulative_provider_evidence: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_cumulative: dict[str, Any] = field(default_factory=dict)
    rollback_cumulative: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_cumulative: dict[str, Any] = field(default_factory=dict)
    trace_provider_sanitization_cumulative: dict[str, Any] = field(default_factory=dict)
    botdb_stability_trend: dict[str, Any] = field(default_factory=dict)
    quality_micro_shift_cumulative: dict[str, Any] = field(default_factory=dict)
    no_mutation_proof: dict[str, Any] = field(default_factory=dict)
    controlled_cohort_expansion_readiness: dict[str, Any] = field(default_factory=dict)
    future_cleanup_stabilization_requirement: dict[str, Any] = field(default_factory=dict)
    consolidation_scorecard: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.cumulative_provider_evidence = _safe_dict(self.cumulative_provider_evidence)
        self.normal_user_no_effect_cumulative = _safe_dict(self.normal_user_no_effect_cumulative)
        self.rollback_cumulative = _safe_dict(self.rollback_cumulative)
        self.safety_kb_boundary_cumulative = _safe_dict(self.safety_kb_boundary_cumulative)
        self.trace_provider_sanitization_cumulative = _safe_dict(self.trace_provider_sanitization_cumulative)
        self.botdb_stability_trend = _safe_dict(self.botdb_stability_trend)
        self.quality_micro_shift_cumulative = _safe_dict(self.quality_micro_shift_cumulative)
        self.no_mutation_proof = _safe_dict(self.no_mutation_proof)
        self.controlled_cohort_expansion_readiness = _safe_dict(self.controlled_cohort_expansion_readiness)
        self.future_cleanup_stabilization_requirement = _safe_dict(self.future_cleanup_stabilization_requirement)
        self.consolidation_scorecard = _safe_dict(self.consolidation_scorecard)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "cumulative_provider_evidence": dict(self.cumulative_provider_evidence),
            "normal_user_no_effect_cumulative": dict(self.normal_user_no_effect_cumulative),
            "rollback_cumulative": dict(self.rollback_cumulative),
            "safety_kb_boundary_cumulative": dict(self.safety_kb_boundary_cumulative),
            "trace_provider_sanitization_cumulative": dict(self.trace_provider_sanitization_cumulative),
            "botdb_stability_trend": dict(self.botdb_stability_trend),
            "quality_micro_shift_cumulative": dict(self.quality_micro_shift_cumulative),
            "no_mutation_proof": dict(self.no_mutation_proof),
            "controlled_cohort_expansion_readiness": dict(self.controlled_cohort_expansion_readiness),
            "future_cleanup_stabilization_requirement": dict(self.future_cleanup_stabilization_requirement),
            "consolidation_scorecard": dict(self.consolidation_scorecard),
        }
