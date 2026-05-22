"""Contracts for PRD-046.1.36 creator-live pilot acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.36"
SOURCE_PRD_ID = "PRD-046.1.35-HF4"


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
class CreatorLivePilotAcceptanceScorecard:
    schema_version: str = "diagnostic_center_creator_live_pilot_acceptance_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_creator_live_pilot"

    source_gate: str = "blocked"
    runtime_readiness_gate: str = "blocked"
    admin_runtime_controls_gate: str = "blocked"
    creator_live_pilot_acceptance_gate: str = "blocked"
    diagnostic_center_trace_acceptance_gate: str = "blocked"
    rollback_force_disabled_gate: str = "blocked"
    normal_user_no_effect_gate: str = "blocked"
    rag_and_behavior_regression_gate: str = "blocked"
    trace_sanitization_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    creator_cases_total: int = 0
    creator_cases_passed: int = 0
    creator_answer_received_count: int = 0
    diagnostic_center_active_for_creator_count: int = 0
    diagnostic_center_trace_present_count: int = 0
    admin_controls_present: bool = False
    force_disabled_toggle_present: bool = False
    all_users_control_locked: bool = False

    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False

    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_prd_recommendation: str = "PRD-046.1.37 - Diagnostic Center Final Results / Completion Decision Gate v1"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_pilot_acceptance_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_creator_live_pilot")
        for field_name in (
            "source_gate",
            "runtime_readiness_gate",
            "admin_runtime_controls_gate",
            "creator_live_pilot_acceptance_gate",
            "diagnostic_center_trace_acceptance_gate",
            "rollback_force_disabled_gate",
            "normal_user_no_effect_gate",
            "rag_and_behavior_regression_gate",
            "trace_sanitization_gate",
            "provider_budget_gate",
            "no_mutation_proof",
            "artifact_encoding_hygiene",
        ):
            setattr(self, field_name, _as_str(getattr(self, field_name), "blocked"))
        for field_name in (
            "creator_cases_total",
            "creator_cases_passed",
            "creator_answer_received_count",
            "diagnostic_center_active_for_creator_count",
            "diagnostic_center_trace_present_count",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0))
        for field_name in (
            "admin_controls_present",
            "force_disabled_toggle_present",
            "all_users_control_locked",
            "broad_rollout_allowed",
            "production_ready",
            "normal_user_activation_allowed",
            "all_users_mode_enabled",
        ):
            setattr(self, field_name, _as_bool(getattr(self, field_name), False))
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]
        self.next_prd_recommendation = _as_str(
            self.next_prd_recommendation,
            "PRD-046.1.37 - Diagnostic Center Final Results / Completion Decision Gate v1",
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class CreatorLivePilotAcceptanceDecision:
    schema_version: str = "diagnostic_center_creator_live_pilot_acceptance_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "blocked_creator_live_pilot"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_pilot_acceptance_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_creator_live_pilot")
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "CreatorLivePilotAcceptanceScorecard",
    "CreatorLivePilotAcceptanceDecision",
]

