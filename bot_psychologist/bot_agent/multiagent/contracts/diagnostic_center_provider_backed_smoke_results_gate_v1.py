"""Contracts for PRD-046.1.24 provider-backed smoke results gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ProviderBackedSmokeResultsDecisionV1:
    schema_version: str = "diagnostic_center_provider_backed_smoke_results_decision_v1"
    prd: str = "PRD-046.1.24"
    final_status: str = "failed"
    decision: str = "fix_required"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = "PRD-046.1.25 - Diagnostic Center Provider-Backed Smoke Calibration v1"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_provider_backed_smoke_results_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.24")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "fix_required")
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]
        self.recommended_next_prd = _as_str(
            self.recommended_next_prd,
            "PRD-046.1.25 - Diagnostic Center Provider-Backed Smoke Calibration v1",
        )

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
class ProviderBackedSmokeResultsGateRunV1:
    schema_version: str = "diagnostic_center_provider_backed_smoke_results_gate_run_v1"
    prd: str = "PRD-046.1.24"
    source_gate: dict[str, Any] = field(default_factory=dict)
    provider_execution_evidence_review: dict[str, Any] = field(default_factory=dict)
    provider_budget_review: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_review: dict[str, Any] = field(default_factory=dict)
    quality_consolidation_review: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_consolidation: dict[str, Any] = field(default_factory=dict)
    provider_output_sanitization_consolidation: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_consolidation: dict[str, Any] = field(default_factory=dict)
    rollback_evidence_review: dict[str, Any] = field(default_factory=dict)
    botdb_stability_review: dict[str, Any] = field(default_factory=dict)
    hard_stop_absence_review: dict[str, Any] = field(default_factory=dict)
    no_mutation_review: dict[str, Any] = field(default_factory=dict)
    risk_register: dict[str, Any] = field(default_factory=dict)
    decision_gate: dict[str, Any] = field(default_factory=dict)
    scorecard: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_provider_backed_smoke_results_gate_run_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.24")
        self.source_gate = _safe_dict(self.source_gate)
        self.provider_execution_evidence_review = _safe_dict(self.provider_execution_evidence_review)
        self.provider_budget_review = _safe_dict(self.provider_budget_review)
        self.normal_user_no_effect_review = _safe_dict(self.normal_user_no_effect_review)
        self.quality_consolidation_review = _safe_dict(self.quality_consolidation_review)
        self.safety_kb_boundary_consolidation = _safe_dict(self.safety_kb_boundary_consolidation)
        self.provider_output_sanitization_consolidation = _safe_dict(self.provider_output_sanitization_consolidation)
        self.trace_sanitization_consolidation = _safe_dict(self.trace_sanitization_consolidation)
        self.rollback_evidence_review = _safe_dict(self.rollback_evidence_review)
        self.botdb_stability_review = _safe_dict(self.botdb_stability_review)
        self.hard_stop_absence_review = _safe_dict(self.hard_stop_absence_review)
        self.no_mutation_review = _safe_dict(self.no_mutation_review)
        self.risk_register = _safe_dict(self.risk_register)
        self.decision_gate = _safe_dict(self.decision_gate)
        self.scorecard = _safe_dict(self.scorecard)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_gate": dict(self.source_gate),
            "provider_execution_evidence_review": dict(self.provider_execution_evidence_review),
            "provider_budget_review": dict(self.provider_budget_review),
            "normal_user_no_effect_review": dict(self.normal_user_no_effect_review),
            "quality_consolidation_review": dict(self.quality_consolidation_review),
            "safety_kb_boundary_consolidation": dict(self.safety_kb_boundary_consolidation),
            "provider_output_sanitization_consolidation": dict(self.provider_output_sanitization_consolidation),
            "trace_sanitization_consolidation": dict(self.trace_sanitization_consolidation),
            "rollback_evidence_review": dict(self.rollback_evidence_review),
            "botdb_stability_review": dict(self.botdb_stability_review),
            "hard_stop_absence_review": dict(self.hard_stop_absence_review),
            "no_mutation_review": dict(self.no_mutation_review),
            "risk_register": dict(self.risk_register),
            "decision_gate": dict(self.decision_gate),
            "scorecard": dict(self.scorecard),
        }
