"""Contracts for PRD-046.1.35 creator live results gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.35"
SOURCE_PRD_ID = "PRD-046.1.34"


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


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass
class SourceArtifactsManifest:
    schema_version: str = "diagnostic_center_creator_live_results_source_manifest_v1"
    prd_id: str = PRD_ID
    source_prd_id: str = SOURCE_PRD_ID
    required_artifact_count: int = 0
    present_artifact_count: int = 0
    missing_artifact_count: int = 0
    parse_error_count: int = 0
    report_consistency_warning_count: int = 0
    source_artifacts_gate: str = "blocked"
    missing_artifacts: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    consistency_warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_results_source_manifest_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.source_prd_id = _as_str(self.source_prd_id, SOURCE_PRD_ID)
        self.required_artifact_count = _as_int(self.required_artifact_count, 0)
        self.present_artifact_count = _as_int(self.present_artifact_count, 0)
        self.missing_artifact_count = _as_int(self.missing_artifact_count, 0)
        self.parse_error_count = _as_int(self.parse_error_count, 0)
        self.report_consistency_warning_count = _as_int(self.report_consistency_warning_count, 0)
        self.source_artifacts_gate = _as_str(self.source_artifacts_gate, "blocked")
        self.missing_artifacts = [str(item) for item in _safe_list(self.missing_artifacts)]
        self.parse_errors = [str(item) for item in _safe_list(self.parse_errors)]
        self.consistency_warnings = [str(item) for item in _safe_list(self.consistency_warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class EvidenceStrengthAudit:
    schema_version: str = "diagnostic_center_creator_live_results_evidence_strength_audit_v1"
    prd_id: str = PRD_ID
    evidence_strength_gate: str = "blocked"
    actual_live_turn_evidence_count: int = 0
    runtime_probe_evidence_count: int = 0
    simulated_gate_evidence_count: int = 0
    missing_evidence_count: int = 0
    strong_evidence_count: int = 0
    medium_evidence_count: int = 0
    weak_evidence_count: int = 0
    missing_strength_count: int = 0
    items: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_results_evidence_strength_audit_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.evidence_strength_gate = _as_str(self.evidence_strength_gate, "blocked")
        self.actual_live_turn_evidence_count = _as_int(self.actual_live_turn_evidence_count, 0)
        self.runtime_probe_evidence_count = _as_int(self.runtime_probe_evidence_count, 0)
        self.simulated_gate_evidence_count = _as_int(self.simulated_gate_evidence_count, 0)
        self.missing_evidence_count = _as_int(self.missing_evidence_count, 0)
        self.strong_evidence_count = _as_int(self.strong_evidence_count, 0)
        self.medium_evidence_count = _as_int(self.medium_evidence_count, 0)
        self.weak_evidence_count = _as_int(self.weak_evidence_count, 0)
        self.missing_strength_count = _as_int(self.missing_strength_count, 0)
        self.items = [dict(item) for item in _safe_list(self.items) if isinstance(item, dict)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ResultsScorecard:
    schema_version: str = "diagnostic_center_creator_live_results_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_fix_required"
    source_artifacts_gate: str = "blocked"
    evidence_strength_gate: str = "blocked"
    live_results_quality_gate: str = "blocked"
    rollback_quality_gate: str = "blocked"
    normal_user_boundary_gate: str = "blocked"
    trace_sanitization_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    docs_consistency_gate: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"
    actual_live_turn_evidence_count: int = 0
    runtime_probe_evidence_count: int = 0
    simulated_gate_evidence_count: int = 0
    missing_evidence_count: int = 0
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    next_prd_recommendation: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_results_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_fix_required")
        self.source_artifacts_gate = _as_str(self.source_artifacts_gate, "blocked")
        self.evidence_strength_gate = _as_str(self.evidence_strength_gate, "blocked")
        self.live_results_quality_gate = _as_str(self.live_results_quality_gate, "blocked")
        self.rollback_quality_gate = _as_str(self.rollback_quality_gate, "blocked")
        self.normal_user_boundary_gate = _as_str(self.normal_user_boundary_gate, "blocked")
        self.trace_sanitization_gate = _as_str(self.trace_sanitization_gate, "blocked")
        self.provider_budget_gate = _as_str(self.provider_budget_gate, "blocked")
        self.no_mutation_proof = _as_str(self.no_mutation_proof, "blocked")
        self.docs_consistency_gate = _as_str(self.docs_consistency_gate, "blocked")
        self.artifact_encoding_hygiene = _as_str(self.artifact_encoding_hygiene, "blocked")
        self.actual_live_turn_evidence_count = _as_int(self.actual_live_turn_evidence_count, 0)
        self.runtime_probe_evidence_count = _as_int(self.runtime_probe_evidence_count, 0)
        self.simulated_gate_evidence_count = _as_int(self.simulated_gate_evidence_count, 0)
        self.missing_evidence_count = _as_int(self.missing_evidence_count, 0)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.next_prd_recommendation = _as_str(self.next_prd_recommendation, "")
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ResultsDecision:
    schema_version: str = "diagnostic_center_creator_live_results_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_fix_required"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_results_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_fix_required")
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "SourceArtifactsManifest",
    "EvidenceStrengthAudit",
    "ResultsScorecard",
    "ResultsDecision",
]

