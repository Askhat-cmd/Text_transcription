"""Contracts for PRD-046.1.37-HF1 runtime timeout evidence repair gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.37-HF1"
SOURCE_PRD_ID = "PRD-046.1.37"


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass
class DiagnosticCenterFinalCompletionHF1Scorecard:
    schema_version: str = "diagnostic_center_actual_live_runtime_hf1_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_runtime_readiness_after_hf1"

    source_gate: str = "blocked"
    docs_state_pre_rerun_correction: str = "blocked"
    endpoint_matrix_probe: str = "blocked"
    adaptive_timeout_diagnosis: str = "blocked"
    latency_profile_gate: str = "blocked"
    actual_live_creator_smoke_gate: str = "blocked"
    trace_acceptance_gate: str = "blocked"
    rollback_hard_stop_live_gate: str = "blocked"
    normal_user_live_no_effect_gate: str = "blocked"
    rag_behavior_regression_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    actual_live_cases_total: int = 0
    actual_live_cases_passed: int = 0
    recommended_runner_timeout_sec: int = 60

    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False
    diagnostic_center_track_closed: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    backlog_items: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_actual_live_runtime_hf1_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_runtime_readiness_after_hf1")
        for field_name in (
            "source_gate",
            "docs_state_pre_rerun_correction",
            "endpoint_matrix_probe",
            "adaptive_timeout_diagnosis",
            "latency_profile_gate",
            "actual_live_creator_smoke_gate",
            "trace_acceptance_gate",
            "rollback_hard_stop_live_gate",
            "normal_user_live_no_effect_gate",
            "rag_behavior_regression_gate",
            "provider_budget_gate",
            "no_mutation_proof",
            "artifact_encoding_hygiene",
        ):
            setattr(self, field_name, _as_str(getattr(self, field_name), "blocked"))
        self.actual_live_cases_total = _as_int(self.actual_live_cases_total, 0)
        self.actual_live_cases_passed = _as_int(self.actual_live_cases_passed, 0)
        self.recommended_runner_timeout_sec = _as_int(self.recommended_runner_timeout_sec, 60)
        for field_name in (
            "broad_rollout_allowed",
            "production_ready",
            "normal_user_activation_allowed",
            "all_users_mode_enabled",
            "diagnostic_center_track_closed",
        ):
            setattr(self, field_name, _as_bool(getattr(self, field_name), False))
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]
        self.backlog_items = [str(x) for x in _safe_list(self.backlog_items)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "DiagnosticCenterFinalCompletionHF1Scorecard",
]
