"""Contracts for PRD-046.1.25 second provider-backed limited smoke."""

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
class SecondProviderBackedSmokeStatusV1:
    final_status: str = "failed"
    decision: str = "hotfix_required"
    source_gate_passed: bool = False
    botdb_live_preflight_passed: bool = False
    provider_availability_preflight_passed: bool = False
    execution_window_count: int = 0
    target_user_count: int = 0
    pilot_scenarios_executed: int = 0
    pilot_apply_count: int = 0
    provider_calls_performed: int = 0
    normal_user_control_count: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_calls: int = 0
    quality_micro_shift_status: str = "failed"
    safety_kb_boundary_status: str = "failed"
    trace_sanitization_status: str = "failed"
    rollback_precheck_passed: bool = False
    rollback_postcheck_passed: bool = False
    hard_stop_triggered: bool = True
    dashboard_chroma_status: str = ""
    dashboard_chroma_count: int = -1
    registry_sources_count: int = -1
    query_http_200: bool = False
    semantic_fallback_used: bool = True
    botdb_circuit_open: bool = True
    production_mutation_detected: bool = True
    artifact_encoding_hygiene_passed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "hotfix_required")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.botdb_live_preflight_passed = _as_bool(self.botdb_live_preflight_passed, False)
        self.provider_availability_preflight_passed = _as_bool(self.provider_availability_preflight_passed, False)
        self.execution_window_count = _as_int(self.execution_window_count, 0)
        self.target_user_count = _as_int(self.target_user_count, 0)
        self.pilot_scenarios_executed = _as_int(self.pilot_scenarios_executed, 0)
        self.pilot_apply_count = _as_int(self.pilot_apply_count, 0)
        self.provider_calls_performed = _as_int(self.provider_calls_performed, 0)
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_calls = _as_int(self.normal_user_provider_calls, 0)
        self.quality_micro_shift_status = _as_str(self.quality_micro_shift_status, "failed")
        self.safety_kb_boundary_status = _as_str(self.safety_kb_boundary_status, "failed")
        self.trace_sanitization_status = _as_str(self.trace_sanitization_status, "failed")
        self.rollback_precheck_passed = _as_bool(self.rollback_precheck_passed, False)
        self.rollback_postcheck_passed = _as_bool(self.rollback_postcheck_passed, False)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, True)
        self.dashboard_chroma_status = _as_str(self.dashboard_chroma_status, "")
        self.dashboard_chroma_count = _as_int(self.dashboard_chroma_count, -1)
        self.registry_sources_count = _as_int(self.registry_sources_count, -1)
        self.query_http_200 = _as_bool(self.query_http_200, False)
        self.semantic_fallback_used = _as_bool(self.semantic_fallback_used, True)
        self.botdb_circuit_open = _as_bool(self.botdb_circuit_open, True)
        self.production_mutation_detected = _as_bool(self.production_mutation_detected, True)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.next_recommended_prd = _as_str(self.next_recommended_prd, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "botdb_live_preflight_passed": self.botdb_live_preflight_passed,
            "provider_availability_preflight_passed": self.provider_availability_preflight_passed,
            "execution_window_count": self.execution_window_count,
            "target_user_count": self.target_user_count,
            "pilot_scenarios_executed": self.pilot_scenarios_executed,
            "pilot_apply_count": self.pilot_apply_count,
            "provider_calls_performed": self.provider_calls_performed,
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_calls": self.normal_user_provider_calls,
            "quality_micro_shift_status": self.quality_micro_shift_status,
            "safety_kb_boundary_status": self.safety_kb_boundary_status,
            "trace_sanitization_status": self.trace_sanitization_status,
            "rollback_precheck_passed": self.rollback_precheck_passed,
            "rollback_postcheck_passed": self.rollback_postcheck_passed,
            "hard_stop_triggered": self.hard_stop_triggered,
            "dashboard_chroma_status": self.dashboard_chroma_status,
            "dashboard_chroma_count": self.dashboard_chroma_count,
            "registry_sources_count": self.registry_sources_count,
            "query_http_200": self.query_http_200,
            "semantic_fallback_used": self.semantic_fallback_used,
            "botdb_circuit_open": self.botdb_circuit_open,
            "production_mutation_detected": self.production_mutation_detected,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "next_recommended_prd": self.next_recommended_prd,
        }


@dataclass
class SecondProviderBackedSmokeDecisionV1:
    schema_version: str = "diagnostic_center_second_provider_backed_smoke_decision_v1"
    prd_id: str = "PRD-046.1.25"
    final_status: str = "failed"
    decision: str = "hotfix_required"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_recommended_prd: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_second_provider_backed_smoke_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.25")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "hotfix_required")
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
class SecondProviderBackedSmokeBundleV1:
    source_gate: dict[str, Any] = field(default_factory=dict)
    botdb_live_preflight: dict[str, Any] = field(default_factory=dict)
    rollback_precheck: dict[str, Any] = field(default_factory=dict)
    execution_manifest: dict[str, Any] = field(default_factory=dict)
    provider_budget_gate: dict[str, Any] = field(default_factory=dict)
    normal_user_no_effect_gate: dict[str, Any] = field(default_factory=dict)
    quality_micro_shift_gate: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_gate: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_gate: dict[str, Any] = field(default_factory=dict)
    rollback_postcheck: dict[str, Any] = field(default_factory=dict)
    botdb_stability_gate: dict[str, Any] = field(default_factory=dict)
    no_mutation_proof: dict[str, Any] = field(default_factory=dict)
    decision_gate: dict[str, Any] = field(default_factory=dict)
    scorecard: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.botdb_live_preflight = _safe_dict(self.botdb_live_preflight)
        self.rollback_precheck = _safe_dict(self.rollback_precheck)
        self.execution_manifest = _safe_dict(self.execution_manifest)
        self.provider_budget_gate = _safe_dict(self.provider_budget_gate)
        self.normal_user_no_effect_gate = _safe_dict(self.normal_user_no_effect_gate)
        self.quality_micro_shift_gate = _safe_dict(self.quality_micro_shift_gate)
        self.safety_kb_boundary_gate = _safe_dict(self.safety_kb_boundary_gate)
        self.trace_sanitization_gate = _safe_dict(self.trace_sanitization_gate)
        self.rollback_postcheck = _safe_dict(self.rollback_postcheck)
        self.botdb_stability_gate = _safe_dict(self.botdb_stability_gate)
        self.no_mutation_proof = _safe_dict(self.no_mutation_proof)
        self.decision_gate = _safe_dict(self.decision_gate)
        self.scorecard = _safe_dict(self.scorecard)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "botdb_live_preflight": dict(self.botdb_live_preflight),
            "rollback_precheck": dict(self.rollback_precheck),
            "execution_manifest": dict(self.execution_manifest),
            "provider_budget_gate": dict(self.provider_budget_gate),
            "normal_user_no_effect_gate": dict(self.normal_user_no_effect_gate),
            "quality_micro_shift_gate": dict(self.quality_micro_shift_gate),
            "safety_kb_boundary_gate": dict(self.safety_kb_boundary_gate),
            "trace_sanitization_gate": dict(self.trace_sanitization_gate),
            "rollback_postcheck": dict(self.rollback_postcheck),
            "botdb_stability_gate": dict(self.botdb_stability_gate),
            "no_mutation_proof": dict(self.no_mutation_proof),
            "decision_gate": dict(self.decision_gate),
            "scorecard": dict(self.scorecard),
        }
