"""Contracts for PRD-046.1.37 final completion decision gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.37"
SOURCE_PRD_ID = "PRD-046.1.36"


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
class DiagnosticCenterFinalCompletionScorecard:
    schema_version: str = "diagnostic_center_final_completion_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_actual_live_evidence"

    source_gate: str = "blocked"
    evidence_provenance_gate: str = "blocked"
    runtime_readiness_final_gate: str = "blocked"
    actual_live_creator_smoke_gate: str = "blocked"
    admin_runtime_controls_final_gate: str = "blocked"
    rollback_hard_stop_final_gate: str = "blocked"
    normal_user_final_no_effect_gate: str = "blocked"
    rag_behavior_final_regression_gate: str = "blocked"
    trace_sanitization_final_gate: str = "blocked"
    provider_budget_final_gate: str = "blocked"
    no_mutation_final_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    actual_live_cases_total: int = 0
    actual_live_cases_passed: int = 0
    diagnostic_center_active_for_creator_count: int = 0
    diagnostic_center_trace_present_count: int = 0
    normal_user_live_authority_applied: bool = False

    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False

    diagnostic_center_track_closed: bool = False
    next_track_recommendation: str = "Multiagent Quality & Tuning Track"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    backlog_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_final_completion_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_actual_live_evidence")
        for field_name in (
            "source_gate",
            "evidence_provenance_gate",
            "runtime_readiness_final_gate",
            "actual_live_creator_smoke_gate",
            "admin_runtime_controls_final_gate",
            "rollback_hard_stop_final_gate",
            "normal_user_final_no_effect_gate",
            "rag_behavior_final_regression_gate",
            "trace_sanitization_final_gate",
            "provider_budget_final_gate",
            "no_mutation_final_proof",
            "artifact_encoding_hygiene",
        ):
            setattr(self, field_name, _as_str(getattr(self, field_name), "blocked"))
        for field_name in (
            "actual_live_cases_total",
            "actual_live_cases_passed",
            "diagnostic_center_active_for_creator_count",
            "diagnostic_center_trace_present_count",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0))
        for field_name in (
            "normal_user_live_authority_applied",
            "broad_rollout_allowed",
            "production_ready",
            "normal_user_activation_allowed",
            "all_users_mode_enabled",
            "diagnostic_center_track_closed",
        ):
            setattr(self, field_name, _as_bool(getattr(self, field_name), False))
        self.next_track_recommendation = _as_str(self.next_track_recommendation, "Multiagent Quality & Tuning Track")
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]
        self.backlog_items = [str(x) for x in _safe_list(self.backlog_items)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class DiagnosticCenterFinalCompletionDecision:
    schema_version: str = "diagnostic_center_final_completion_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_actual_live_evidence"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_final_completion_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_actual_live_evidence")
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "DiagnosticCenterFinalCompletionScorecard",
    "DiagnosticCenterFinalCompletionDecision",
]

