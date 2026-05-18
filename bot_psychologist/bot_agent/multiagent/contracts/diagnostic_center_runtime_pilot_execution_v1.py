"""Contracts for PRD-046.1.20 controlled runtime pilot execution gate."""

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
class DiagnosticCenterRuntimePilotExecutionStatus:
    final_status: str = "failed"
    decision: str = "blocked_runtime_pilot_execution"
    source_gate_passed: bool = False
    preflight_gate_passed: bool = False
    execution_window_count: int = 0
    target_user_count: int = 0
    pilot_apply_only_for_allowed_user: bool = False
    normal_user_control_count: int = 0
    normal_user_apply_count: int = 0
    writer_prompt_changed_for_normal_user: bool = False
    writer_contract_changed_for_normal_user: bool = False
    final_answer_changed_for_normal_user: bool = False
    rollback_precheck_passed: bool = False
    rollback_postcheck_passed: bool = False
    stale_apply_after_force_disabled_count: int = 0
    quality_delta_status: str = "failed"
    candidate_weaker_than_baseline_count: int = 0
    safety_kb_boundary_gate_passed: bool = False
    trace_sanitization_gate_passed: bool = False
    hard_stop_triggered: bool = True
    production_mutation_detected: bool = True
    all_blocks_merged_mutated: bool = False
    registry_mutated: bool = False
    config_mutated: bool = False
    chroma_reindex_performed: bool = False
    runtime_defaults_changed: bool = False
    artifact_encoding_hygiene_passed: bool = False
    docs_synced: bool = False

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_runtime_pilot_execution")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.preflight_gate_passed = _as_bool(self.preflight_gate_passed, False)
        self.execution_window_count = _as_int(self.execution_window_count, 0)
        self.target_user_count = _as_int(self.target_user_count, 0)
        self.pilot_apply_only_for_allowed_user = _as_bool(self.pilot_apply_only_for_allowed_user, False)
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.writer_prompt_changed_for_normal_user = _as_bool(self.writer_prompt_changed_for_normal_user, False)
        self.writer_contract_changed_for_normal_user = _as_bool(self.writer_contract_changed_for_normal_user, False)
        self.final_answer_changed_for_normal_user = _as_bool(self.final_answer_changed_for_normal_user, False)
        self.rollback_precheck_passed = _as_bool(self.rollback_precheck_passed, False)
        self.rollback_postcheck_passed = _as_bool(self.rollback_postcheck_passed, False)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0)
        self.quality_delta_status = _as_str(self.quality_delta_status, "failed")
        self.candidate_weaker_than_baseline_count = _as_int(self.candidate_weaker_than_baseline_count, 0)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)
        self.trace_sanitization_gate_passed = _as_bool(self.trace_sanitization_gate_passed, False)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, True)
        self.production_mutation_detected = _as_bool(self.production_mutation_detected, True)
        self.all_blocks_merged_mutated = _as_bool(self.all_blocks_merged_mutated, False)
        self.registry_mutated = _as_bool(self.registry_mutated, False)
        self.config_mutated = _as_bool(self.config_mutated, False)
        self.chroma_reindex_performed = _as_bool(self.chroma_reindex_performed, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.docs_synced = _as_bool(self.docs_synced, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "preflight_gate_passed": self.preflight_gate_passed,
            "execution_window_count": self.execution_window_count,
            "target_user_count": self.target_user_count,
            "pilot_apply_only_for_allowed_user": self.pilot_apply_only_for_allowed_user,
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_count": self.normal_user_apply_count,
            "writer_prompt_changed_for_normal_user": self.writer_prompt_changed_for_normal_user,
            "writer_contract_changed_for_normal_user": self.writer_contract_changed_for_normal_user,
            "final_answer_changed_for_normal_user": self.final_answer_changed_for_normal_user,
            "rollback_precheck_passed": self.rollback_precheck_passed,
            "rollback_postcheck_passed": self.rollback_postcheck_passed,
            "stale_apply_after_force_disabled_count": self.stale_apply_after_force_disabled_count,
            "quality_delta_status": self.quality_delta_status,
            "candidate_weaker_than_baseline_count": self.candidate_weaker_than_baseline_count,
            "safety_kb_boundary_gate_passed": self.safety_kb_boundary_gate_passed,
            "trace_sanitization_gate_passed": self.trace_sanitization_gate_passed,
            "hard_stop_triggered": self.hard_stop_triggered,
            "production_mutation_detected": self.production_mutation_detected,
            "all_blocks_merged_mutated": self.all_blocks_merged_mutated,
            "registry_mutated": self.registry_mutated,
            "config_mutated": self.config_mutated,
            "chroma_reindex_performed": self.chroma_reindex_performed,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "docs_synced": self.docs_synced,
        }


@dataclass
class DiagnosticCenterRuntimePilotExecutionDecision:
    schema_version: str = "diagnostic_center_runtime_pilot_execution_decision_v1"
    prd_id: str = "PRD-046.1.20"
    final_status: str = "failed"
    decision: str = "blocked_runtime_pilot_execution"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = "PRD-046.1.20-HF1 - Runtime pilot execution blocker hotfix"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_runtime_pilot_execution_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.20")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_runtime_pilot_execution")
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]
        self.recommended_next_prd = _as_str(self.recommended_next_prd, "PRD-046.1.20-HF1 - Runtime pilot execution blocker hotfix")

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
class DiagnosticCenterRuntimePilotExecutionBundle:
    source_gate: dict[str, Any] = field(default_factory=dict)
    preflight_gate: dict[str, Any] = field(default_factory=dict)
    execution_manifest: dict[str, Any] = field(default_factory=dict)
    toggle_state_before: dict[str, Any] = field(default_factory=dict)
    rollback_precheck: dict[str, Any] = field(default_factory=dict)
    pilot_operator_execution: dict[str, Any] = field(default_factory=dict)
    normal_user_control_execution: dict[str, Any] = field(default_factory=dict)
    limited_live_smoke_results: dict[str, Any] = field(default_factory=dict)
    baseline_vs_pilot_quality_delta: dict[str, Any] = field(default_factory=dict)
    safety_kb_boundary_gate: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_gate: dict[str, Any] = field(default_factory=dict)
    rollback_postcheck: dict[str, Any] = field(default_factory=dict)
    hard_stop_evaluation: dict[str, Any] = field(default_factory=dict)
    monitoring_scorecard: dict[str, Any] = field(default_factory=dict)
    no_mutation_status: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene_status: dict[str, Any] = field(default_factory=dict)
    execution_decision: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.preflight_gate = _safe_dict(self.preflight_gate)
        self.execution_manifest = _safe_dict(self.execution_manifest)
        self.toggle_state_before = _safe_dict(self.toggle_state_before)
        self.rollback_precheck = _safe_dict(self.rollback_precheck)
        self.pilot_operator_execution = _safe_dict(self.pilot_operator_execution)
        self.normal_user_control_execution = _safe_dict(self.normal_user_control_execution)
        self.limited_live_smoke_results = _safe_dict(self.limited_live_smoke_results)
        self.baseline_vs_pilot_quality_delta = _safe_dict(self.baseline_vs_pilot_quality_delta)
        self.safety_kb_boundary_gate = _safe_dict(self.safety_kb_boundary_gate)
        self.trace_sanitization_gate = _safe_dict(self.trace_sanitization_gate)
        self.rollback_postcheck = _safe_dict(self.rollback_postcheck)
        self.hard_stop_evaluation = _safe_dict(self.hard_stop_evaluation)
        self.monitoring_scorecard = _safe_dict(self.monitoring_scorecard)
        self.no_mutation_status = _safe_dict(self.no_mutation_status)
        self.artifact_hygiene_status = _safe_dict(self.artifact_hygiene_status)
        self.execution_decision = _safe_dict(self.execution_decision)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "preflight_gate": dict(self.preflight_gate),
            "execution_manifest": dict(self.execution_manifest),
            "toggle_state_before": dict(self.toggle_state_before),
            "rollback_precheck": dict(self.rollback_precheck),
            "pilot_operator_execution": dict(self.pilot_operator_execution),
            "normal_user_control_execution": dict(self.normal_user_control_execution),
            "limited_live_smoke_results": dict(self.limited_live_smoke_results),
            "baseline_vs_pilot_quality_delta": dict(self.baseline_vs_pilot_quality_delta),
            "safety_kb_boundary_gate": dict(self.safety_kb_boundary_gate),
            "trace_sanitization_gate": dict(self.trace_sanitization_gate),
            "rollback_postcheck": dict(self.rollback_postcheck),
            "hard_stop_evaluation": dict(self.hard_stop_evaluation),
            "monitoring_scorecard": dict(self.monitoring_scorecard),
            "no_mutation_status": dict(self.no_mutation_status),
            "artifact_hygiene_status": dict(self.artifact_hygiene_status),
            "execution_decision": dict(self.execution_decision),
        }
