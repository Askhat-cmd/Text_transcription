"""Contracts for PRD-046.1.28 final runtime governance acceptance gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_FINAL_STATUS = {"passed", "blocked"}
ALLOWED_DECISIONS = {
    "accepted_ready_for_cleanup_stabilization",
    "blocked_requires_hotfix",
    "blocked_requires_additional_limited_evidence",
}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class DiagnosticCenterFinalRuntimeGovernanceAcceptanceV1:
    prd_id: str = "PRD-046.1.28"
    final_status: str = "blocked"
    decision: str = "blocked_requires_hotfix"
    source_chain: dict[str, Any] = field(default_factory=dict)
    provider_evidence: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect: dict[str, Any] = field(default_factory=dict)
    rollback_hard_stop: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary: dict[str, Any] = field(default_factory=dict)
    trace_provider_sanitization: dict[str, Any] = field(default_factory=dict)
    botdb_stability: dict[str, Any] = field(default_factory=dict)
    quality_micro_shift: dict[str, Any] = field(default_factory=dict)
    permanent_regression_gates: dict[str, Any] = field(default_factory=dict)
    runtime_governance_boundaries: dict[str, Any] = field(default_factory=dict)
    cleanup_stabilization_readiness: dict[str, Any] = field(default_factory=dict)
    no_mutation_proof: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene: dict[str, Any] = field(default_factory=dict)
    risk_register: dict[str, Any] = field(default_factory=dict)
    next_prd_recommendation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.28")
        self.final_status = _as_str(self.final_status, "blocked")
        if self.final_status not in ALLOWED_FINAL_STATUS:
            self.final_status = "blocked"

        self.decision = _as_str(self.decision, "blocked_requires_hotfix")
        if self.decision not in ALLOWED_DECISIONS:
            self.decision = "blocked_requires_hotfix"

        self.source_chain = _safe_dict(self.source_chain)
        self.provider_evidence = _safe_dict(self.provider_evidence)
        self.normal_user_no_effect = _safe_dict(self.normal_user_no_effect)
        self.rollback_hard_stop = _safe_dict(self.rollback_hard_stop)
        self.safety_kb_boundary = _safe_dict(self.safety_kb_boundary)
        self.trace_provider_sanitization = _safe_dict(self.trace_provider_sanitization)
        self.botdb_stability = _safe_dict(self.botdb_stability)
        self.quality_micro_shift = _safe_dict(self.quality_micro_shift)
        self.permanent_regression_gates = _safe_dict(self.permanent_regression_gates)
        self.runtime_governance_boundaries = _safe_dict(self.runtime_governance_boundaries)
        self.cleanup_stabilization_readiness = _safe_dict(self.cleanup_stabilization_readiness)
        self.no_mutation_proof = _safe_dict(self.no_mutation_proof)
        self.artifact_hygiene = _safe_dict(self.artifact_hygiene)
        self.risk_register = _safe_dict(self.risk_register)
        self.next_prd_recommendation = _safe_dict(self.next_prd_recommendation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "diagnostic_center_final_runtime_governance_acceptance_v1",
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "source_chain": dict(self.source_chain),
            "provider_evidence": dict(self.provider_evidence),
            "normal_user_no_effect": dict(self.normal_user_no_effect),
            "rollback_hard_stop": dict(self.rollback_hard_stop),
            "safety_kb_boundary": dict(self.safety_kb_boundary),
            "trace_provider_sanitization": dict(self.trace_provider_sanitization),
            "botdb_stability": dict(self.botdb_stability),
            "quality_micro_shift": dict(self.quality_micro_shift),
            "permanent_regression_gates": dict(self.permanent_regression_gates),
            "runtime_governance_boundaries": dict(self.runtime_governance_boundaries),
            "cleanup_stabilization_readiness": dict(self.cleanup_stabilization_readiness),
            "no_mutation_proof": dict(self.no_mutation_proof),
            "artifact_hygiene": dict(self.artifact_hygiene),
            "risk_register": dict(self.risk_register),
            "next_prd_recommendation": dict(self.next_prd_recommendation),
        }

