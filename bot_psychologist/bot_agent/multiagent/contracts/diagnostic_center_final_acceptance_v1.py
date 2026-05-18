"""Contracts for PRD-046.1.16 final acceptance / runtime governance closure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class FinalAcceptanceDecisionV1:
    schema_version: str = "diagnostic_center_runtime_governance_closure_decision_v1"
    prd_id: str = "PRD-046.1.16"
    final_status: str = "failed"
    decision: str = "blocked_missing_permanent_regression_gate"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_runtime_governance_closure_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.16")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_missing_permanent_regression_gate")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass
class DiagnosticCenterFinalAcceptanceRunV1:
    schema_version: str = "diagnostic_center_final_acceptance_v1"
    prd: str = "PRD-046.1.16"
    source_prd: str = "PRD-046.1.15"
    mode: str = "audit_deterministic_gates_documentation_sync"
    source_gate: dict[str, Any] = field(default_factory=dict)
    runtime_boundary_status: dict[str, Any] = field(default_factory=dict)
    permanent_regression_gate_status: dict[str, Any] = field(default_factory=dict)
    prompt_constraint_baseline_status: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_status: dict[str, Any] = field(default_factory=dict)
    kb_governance_boundary_status: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_status: dict[str, Any] = field(default_factory=dict)
    no_mutation_status: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene_status: dict[str, Any] = field(default_factory=dict)
    documentation_sync_status: dict[str, Any] = field(default_factory=dict)
    final_acceptance_decision: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_final_acceptance_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.16")
        self.source_prd = _as_str(self.source_prd, "PRD-046.1.15")
        self.mode = _as_str(self.mode, "audit_deterministic_gates_documentation_sync")
        self.source_gate = _safe_dict(self.source_gate)
        self.runtime_boundary_status = _safe_dict(self.runtime_boundary_status)
        self.permanent_regression_gate_status = _safe_dict(self.permanent_regression_gate_status)
        self.prompt_constraint_baseline_status = _safe_dict(self.prompt_constraint_baseline_status)
        self.normal_user_no_effect_status = _safe_dict(self.normal_user_no_effect_status)
        self.kb_governance_boundary_status = _safe_dict(self.kb_governance_boundary_status)
        self.trace_sanitization_status = _safe_dict(self.trace_sanitization_status)
        self.no_mutation_status = _safe_dict(self.no_mutation_status)
        self.artifact_hygiene_status = _safe_dict(self.artifact_hygiene_status)
        self.documentation_sync_status = _safe_dict(self.documentation_sync_status)
        self.final_acceptance_decision = _safe_dict(self.final_acceptance_decision)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_prd": self.source_prd,
            "mode": self.mode,
            "source_gate": dict(self.source_gate),
            "runtime_boundary_status": dict(self.runtime_boundary_status),
            "permanent_regression_gate_status": dict(self.permanent_regression_gate_status),
            "prompt_constraint_baseline_status": dict(self.prompt_constraint_baseline_status),
            "normal_user_no_effect_status": dict(self.normal_user_no_effect_status),
            "kb_governance_boundary_status": dict(self.kb_governance_boundary_status),
            "trace_sanitization_status": dict(self.trace_sanitization_status),
            "no_mutation_status": dict(self.no_mutation_status),
            "artifact_hygiene_status": dict(self.artifact_hygiene_status),
            "documentation_sync_status": dict(self.documentation_sync_status),
            "final_acceptance_decision": dict(self.final_acceptance_decision),
        }
