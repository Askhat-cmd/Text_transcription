"""Contracts for PRD-046.1.23 provider-backed limited smoke execution gate."""

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


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ProviderBackedLimitedSmokeExecutionStatus:
    final_status: str = "failed"
    decision: str = "provider_backed_limited_smoke_failed"
    source_gate_passed: bool = False
    live_dependency_preflight_passed: bool = False
    provider_availability_preflight_passed: bool = False
    execution_window_count: int = 0
    target_user_count: int = 0
    pilot_scenarios_executed: int = 0
    pilot_apply_count: int = 0
    pilot_apply_only_for_allowed_user: bool = False
    provider_calls_performed: int = 0
    all_provider_calls_for_allowed_user: bool = False
    normal_user_control_count: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_apply_count: int = 0
    quality_status: str = "failed"
    safety_kb_boundary_status: str = "failed"
    trace_sanitization_status: str = "failed"
    provider_output_sanitization_status: str = "failed"
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
    no_mutation_proof_passed: bool = False
    artifact_encoding_hygiene_passed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    future_expansion_requires_new_prd: bool = True
    docs_synced: bool = False

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "provider_backed_limited_smoke_failed")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.live_dependency_preflight_passed = _as_bool(self.live_dependency_preflight_passed, False)
        self.provider_availability_preflight_passed = _as_bool(self.provider_availability_preflight_passed, False)
        self.execution_window_count = _as_int(self.execution_window_count, 0)
        self.target_user_count = _as_int(self.target_user_count, 0)
        self.pilot_scenarios_executed = _as_int(self.pilot_scenarios_executed, 0)
        self.pilot_apply_count = _as_int(self.pilot_apply_count, 0)
        self.pilot_apply_only_for_allowed_user = _as_bool(self.pilot_apply_only_for_allowed_user, False)
        self.provider_calls_performed = _as_int(self.provider_calls_performed, 0)
        self.all_provider_calls_for_allowed_user = _as_bool(self.all_provider_calls_for_allowed_user, False)
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_apply_count = _as_int(self.normal_user_provider_apply_count, 0)
        self.quality_status = _as_str(self.quality_status, "failed")
        self.safety_kb_boundary_status = _as_str(self.safety_kb_boundary_status, "failed")
        self.trace_sanitization_status = _as_str(self.trace_sanitization_status, "failed")
        self.provider_output_sanitization_status = _as_str(self.provider_output_sanitization_status, "failed")
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
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.future_expansion_requires_new_prd = _as_bool(self.future_expansion_requires_new_prd, True)
        self.docs_synced = _as_bool(self.docs_synced, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "live_dependency_preflight_passed": self.live_dependency_preflight_passed,
            "provider_availability_preflight_passed": self.provider_availability_preflight_passed,
            "execution_window_count": self.execution_window_count,
            "target_user_count": self.target_user_count,
            "pilot_scenarios_executed": self.pilot_scenarios_executed,
            "pilot_apply_count": self.pilot_apply_count,
            "pilot_apply_only_for_allowed_user": self.pilot_apply_only_for_allowed_user,
            "provider_calls_performed": self.provider_calls_performed,
            "all_provider_calls_for_allowed_user": self.all_provider_calls_for_allowed_user,
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_apply_count": self.normal_user_provider_apply_count,
            "quality_status": self.quality_status,
            "safety_kb_boundary_status": self.safety_kb_boundary_status,
            "trace_sanitization_status": self.trace_sanitization_status,
            "provider_output_sanitization_status": self.provider_output_sanitization_status,
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
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "future_expansion_requires_new_prd": self.future_expansion_requires_new_prd,
            "docs_synced": self.docs_synced,
        }


@dataclass
class ProviderBackedLimitedSmokeExecutionDecision:
    schema_version: str = "diagnostic_center_provider_backed_limited_smoke_execution_decision_v1"
    prd_id: str = "PRD-046.1.23"
    final_status: str = "failed"
    decision: str = "provider_backed_limited_smoke_failed"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = "PRD-046.1.23-HF1 - Provider-backed limited smoke blocker hotfix"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_provider_backed_limited_smoke_execution_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.23")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "provider_backed_limited_smoke_failed")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.recommended_next_prd = _as_str(
            self.recommended_next_prd,
            "PRD-046.1.23-HF1 - Provider-backed limited smoke blocker hotfix",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "recommended_next_prd": self.recommended_next_prd,
        }


@dataclass
class ProviderBackedLimitedSmokeExecutionBundle:
    source_gate: dict[str, Any] = field(default_factory=dict)
    live_dependency_preflight: dict[str, Any] = field(default_factory=dict)
    provider_availability_preflight: dict[str, Any] = field(default_factory=dict)
    toggle_state_before: dict[str, Any] = field(default_factory=dict)
    rollback_precheck: dict[str, Any] = field(default_factory=dict)
    execution_manifest: dict[str, Any] = field(default_factory=dict)
    provider_call_budget: dict[str, Any] = field(default_factory=dict)
    pilot_operator_execution: dict[str, Any] = field(default_factory=dict)
    normal_user_controls: dict[str, Any] = field(default_factory=dict)
    quality_review: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_review: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_review: dict[str, Any] = field(default_factory=dict)
    provider_output_sanitization_review: dict[str, Any] = field(default_factory=dict)
    rollback_postcheck: dict[str, Any] = field(default_factory=dict)
    hard_stop_evaluation: dict[str, Any] = field(default_factory=dict)
    no_mutation_proof: dict[str, Any] = field(default_factory=dict)
    execution_scorecard: dict[str, Any] = field(default_factory=dict)
    next_prd_recommendation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.live_dependency_preflight = _safe_dict(self.live_dependency_preflight)
        self.provider_availability_preflight = _safe_dict(self.provider_availability_preflight)
        self.toggle_state_before = _safe_dict(self.toggle_state_before)
        self.rollback_precheck = _safe_dict(self.rollback_precheck)
        self.execution_manifest = _safe_dict(self.execution_manifest)
        self.provider_call_budget = _safe_dict(self.provider_call_budget)
        self.pilot_operator_execution = _safe_dict(self.pilot_operator_execution)
        self.normal_user_controls = _safe_dict(self.normal_user_controls)
        self.quality_review = _safe_dict(self.quality_review)
        self.safety_kb_boundary_review = _safe_dict(self.safety_kb_boundary_review)
        self.trace_sanitization_review = _safe_dict(self.trace_sanitization_review)
        self.provider_output_sanitization_review = _safe_dict(self.provider_output_sanitization_review)
        self.rollback_postcheck = _safe_dict(self.rollback_postcheck)
        self.hard_stop_evaluation = _safe_dict(self.hard_stop_evaluation)
        self.no_mutation_proof = _safe_dict(self.no_mutation_proof)
        self.execution_scorecard = _safe_dict(self.execution_scorecard)
        self.next_prd_recommendation = _safe_dict(self.next_prd_recommendation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "live_dependency_preflight": dict(self.live_dependency_preflight),
            "provider_availability_preflight": dict(self.provider_availability_preflight),
            "toggle_state_before": dict(self.toggle_state_before),
            "rollback_precheck": dict(self.rollback_precheck),
            "execution_manifest": dict(self.execution_manifest),
            "provider_call_budget": dict(self.provider_call_budget),
            "pilot_operator_execution": dict(self.pilot_operator_execution),
            "normal_user_controls": dict(self.normal_user_controls),
            "quality_review": dict(self.quality_review),
            "safety_kb_boundary_review": dict(self.safety_kb_boundary_review),
            "trace_sanitization_review": dict(self.trace_sanitization_review),
            "provider_output_sanitization_review": dict(self.provider_output_sanitization_review),
            "rollback_postcheck": dict(self.rollback_postcheck),
            "hard_stop_evaluation": dict(self.hard_stop_evaluation),
            "no_mutation_proof": dict(self.no_mutation_proof),
            "execution_scorecard": dict(self.execution_scorecard),
            "next_prd_recommendation": dict(self.next_prd_recommendation),
        }
