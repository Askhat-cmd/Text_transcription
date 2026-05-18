"""Contracts for PRD-046.1.21 runtime pilot results/rollback/quality gate."""

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
class RuntimePilotResultsGateSourceStatusV1:
    source_prd: str = "PRD-046.1.20"
    source_final_status: str = "failed"
    source_decision: str = "blocked_runtime_pilot_execution"
    source_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.source_prd = _as_str(self.source_prd, "PRD-046.1.20")
        self.source_final_status = _as_str(self.source_final_status, "failed")
        self.source_decision = _as_str(self.source_decision, "blocked_runtime_pilot_execution")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_prd": self.source_prd,
            "source_final_status": self.source_final_status,
            "source_decision": self.source_decision,
            "source_gate_passed": self.source_gate_passed,
        }


@dataclass
class RuntimePilotResultsDecisionV1:
    schema_version: str = "diagnostic_center_runtime_pilot_results_gate_decision_v1"
    prd: str = "PRD-046.1.21"
    final_status: str = "failed"
    decision: str = "fix_required"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_runtime_pilot_results_gate_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.21")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "fix_required")
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]
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
class RuntimePilotResultsGateRunV1:
    schema_version: str = "diagnostic_center_runtime_pilot_results_gate_run_v1"
    prd: str = "PRD-046.1.21"
    source_gate: dict[str, Any] = field(default_factory=dict)
    execution_evidence_review: dict[str, Any] = field(default_factory=dict)
    rollback_evidence_review: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_review: dict[str, Any] = field(default_factory=dict)
    quality_delta_review: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_review: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_review: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene_review: dict[str, Any] = field(default_factory=dict)
    encoding_warning_review: dict[str, Any] = field(default_factory=dict)
    no_mutation_review: dict[str, Any] = field(default_factory=dict)
    runtime_pilot_results_risk_register: dict[str, Any] = field(default_factory=dict)
    runtime_pilot_results_decision_gate: dict[str, Any] = field(default_factory=dict)
    runtime_pilot_results_scorecard: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_runtime_pilot_results_gate_run_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.21")
        self.source_gate = _safe_dict(self.source_gate)
        self.execution_evidence_review = _safe_dict(self.execution_evidence_review)
        self.rollback_evidence_review = _safe_dict(self.rollback_evidence_review)
        self.normal_user_no_effect_review = _safe_dict(self.normal_user_no_effect_review)
        self.quality_delta_review = _safe_dict(self.quality_delta_review)
        self.safety_kb_boundary_review = _safe_dict(self.safety_kb_boundary_review)
        self.trace_sanitization_review = _safe_dict(self.trace_sanitization_review)
        self.artifact_hygiene_review = _safe_dict(self.artifact_hygiene_review)
        self.encoding_warning_review = _safe_dict(self.encoding_warning_review)
        self.no_mutation_review = _safe_dict(self.no_mutation_review)
        self.runtime_pilot_results_risk_register = _safe_dict(self.runtime_pilot_results_risk_register)
        self.runtime_pilot_results_decision_gate = _safe_dict(self.runtime_pilot_results_decision_gate)
        self.runtime_pilot_results_scorecard = _safe_dict(self.runtime_pilot_results_scorecard)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_gate": dict(self.source_gate),
            "execution_evidence_review": dict(self.execution_evidence_review),
            "rollback_evidence_review": dict(self.rollback_evidence_review),
            "normal_user_no_effect_review": dict(self.normal_user_no_effect_review),
            "quality_delta_review": dict(self.quality_delta_review),
            "safety_kb_boundary_review": dict(self.safety_kb_boundary_review),
            "trace_sanitization_review": dict(self.trace_sanitization_review),
            "artifact_hygiene_review": dict(self.artifact_hygiene_review),
            "encoding_warning_review": dict(self.encoding_warning_review),
            "no_mutation_review": dict(self.no_mutation_review),
            "runtime_pilot_results_risk_register": dict(self.runtime_pilot_results_risk_register),
            "runtime_pilot_results_decision_gate": dict(self.runtime_pilot_results_decision_gate),
            "runtime_pilot_results_scorecard": dict(self.runtime_pilot_results_scorecard),
        }
