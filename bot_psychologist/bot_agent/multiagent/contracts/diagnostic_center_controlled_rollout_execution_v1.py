"""Contracts for PRD-046.1.31 controlled rollout execution gate."""

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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ControlledRolloutSourceGate:
    schema_version: str = "diagnostic_center_controlled_rollout_source_gate_v1"
    prd_id: str = "PRD-046.1.31"
    source_gate_passed: bool = False
    source_artifacts_present: bool = False
    source_artifacts_parseable: bool = False
    source_final_status: str = "blocked"
    source_decision: str = "blocked"
    source_blockers_none: bool = False
    source_warnings_none: bool = False
    no_mutation_proof_passed: bool = False
    docs_synced: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    source_inventory_count: int = 0
    blockers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_source_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.source_artifacts_present = _as_bool(self.source_artifacts_present, False)
        self.source_artifacts_parseable = _as_bool(self.source_artifacts_parseable, False)
        self.source_final_status = _as_str(self.source_final_status, "blocked")
        self.source_decision = _as_str(self.source_decision, "blocked")
        self.source_blockers_none = _as_bool(self.source_blockers_none, False)
        self.source_warnings_none = _as_bool(self.source_warnings_none, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.docs_synced = _as_bool(self.docs_synced, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.source_inventory_count = _as_int(self.source_inventory_count, 0)
        self.blockers = [str(item) for item in _as_list(self.blockers)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "source_gate_passed": self.source_gate_passed,
            "source_artifacts_present": self.source_artifacts_present,
            "source_artifacts_parseable": self.source_artifacts_parseable,
            "source_final_status": self.source_final_status,
            "source_decision": self.source_decision,
            "source_blockers_none": self.source_blockers_none,
            "source_warnings_none": self.source_warnings_none,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "docs_synced": self.docs_synced,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "source_inventory_count": self.source_inventory_count,
            "blockers": list(self.blockers),
        }


@dataclass
class ControlledRolloutCohortPolicy:
    schema_version: str = "diagnostic_center_controlled_rollout_cohort_policy_v1"
    prd_id: str = "PRD-046.1.31"
    max_target_operator_count: int = 3
    target_user_type: str = "allowlisted_internal_or_synthetic_operators_only"
    allowlisted_operator_ids: list[str] = field(default_factory=lambda: ["pilot_runtime_operator_001", "pilot_runtime_operator_002", "pilot_runtime_operator_003"])
    normal_user_activation_allowed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    ready: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_cohort_policy_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.max_target_operator_count = _as_int(self.max_target_operator_count, 3)
        self.target_user_type = _as_str(self.target_user_type, "allowlisted_internal_or_synthetic_operators_only")
        self.allowlisted_operator_ids = [str(item) for item in _as_list(self.allowlisted_operator_ids)]
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.ready = _as_bool(self.ready, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "max_target_operator_count": self.max_target_operator_count,
            "target_user_type": self.target_user_type,
            "allowlisted_operator_ids": list(self.allowlisted_operator_ids),
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "ready": self.ready,
        }


@dataclass
class ControlledRolloutPreflight:
    schema_version: str = "diagnostic_center_controlled_rollout_preflight_v1"
    prd_id: str = "PRD-046.1.31"
    botdb_status_ok: bool = False
    registry_focus_source_only: bool = False
    chroma_count_ok: bool = False
    query_endpoint_200: bool = False
    semantic_fallback_used: bool = True
    botdb_circuit_open: bool = True
    runtime_defaults_conservative: bool = True
    allowlist_explicitly_set: bool = False
    rollback_switch_tested: bool = False
    artifact_output_path_clean: bool = False
    provider_budget_configured: bool = False
    normal_user_controls_configured: bool = False
    preflight_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_preflight_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.botdb_status_ok = _as_bool(self.botdb_status_ok, False)
        self.registry_focus_source_only = _as_bool(self.registry_focus_source_only, False)
        self.chroma_count_ok = _as_bool(self.chroma_count_ok, False)
        self.query_endpoint_200 = _as_bool(self.query_endpoint_200, False)
        self.semantic_fallback_used = _as_bool(self.semantic_fallback_used, True)
        self.botdb_circuit_open = _as_bool(self.botdb_circuit_open, True)
        self.runtime_defaults_conservative = _as_bool(self.runtime_defaults_conservative, True)
        self.allowlist_explicitly_set = _as_bool(self.allowlist_explicitly_set, False)
        self.rollback_switch_tested = _as_bool(self.rollback_switch_tested, False)
        self.artifact_output_path_clean = _as_bool(self.artifact_output_path_clean, False)
        self.provider_budget_configured = _as_bool(self.provider_budget_configured, False)
        self.normal_user_controls_configured = _as_bool(self.normal_user_controls_configured, False)
        self.preflight_passed = _as_bool(self.preflight_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "botdb_status_ok": self.botdb_status_ok,
            "registry_focus_source_only": self.registry_focus_source_only,
            "chroma_count_ok": self.chroma_count_ok,
            "query_endpoint_200": self.query_endpoint_200,
            "semantic_fallback_used": self.semantic_fallback_used,
            "botdb_circuit_open": self.botdb_circuit_open,
            "runtime_defaults_conservative": self.runtime_defaults_conservative,
            "allowlist_explicitly_set": self.allowlist_explicitly_set,
            "rollback_switch_tested": self.rollback_switch_tested,
            "artifact_output_path_clean": self.artifact_output_path_clean,
            "provider_budget_configured": self.provider_budget_configured,
            "normal_user_controls_configured": self.normal_user_controls_configured,
            "preflight_passed": self.preflight_passed,
        }


@dataclass
class ControlledRolloutExecutionManifest:
    schema_version: str = "diagnostic_center_controlled_rollout_execution_manifest_v1"
    prd_id: str = "PRD-046.1.31"
    execution_performed: bool = False
    execution_window_count: int = 1
    target_operator_count: int = 0
    target_operator_ids: list[str] = field(default_factory=list)
    scenario_count: int = 0
    provider_call_budget_max: int = 12
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_execution_manifest_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.execution_performed = _as_bool(self.execution_performed, False)
        self.execution_window_count = _as_int(self.execution_window_count, 1)
        self.target_operator_count = _as_int(self.target_operator_count, 0)
        self.target_operator_ids = [str(item) for item in _as_list(self.target_operator_ids)]
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.provider_call_budget_max = _as_int(self.provider_call_budget_max, 12)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "execution_performed": self.execution_performed,
            "execution_window_count": self.execution_window_count,
            "target_operator_count": self.target_operator_count,
            "target_operator_ids": list(self.target_operator_ids),
            "scenario_count": self.scenario_count,
            "provider_call_budget_max": self.provider_call_budget_max,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
        }


@dataclass
class ControlledRolloutExecutionResult:
    schema_version: str = "diagnostic_center_controlled_rollout_execution_result_v1"
    prd_id: str = "PRD-046.1.31"
    execution_performed: bool = False
    target_operator_count: int = 0
    scenario_count: int = 0
    provider_calls_total: int = 0
    pilot_apply_count: int = 0
    all_provider_calls_for_allowed_user: bool = True
    scenario_groups_covered: list[str] = field(default_factory=list)
    quality_micro_shift_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_execution_result_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.execution_performed = _as_bool(self.execution_performed, False)
        self.target_operator_count = _as_int(self.target_operator_count, 0)
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.pilot_apply_count = _as_int(self.pilot_apply_count, 0)
        self.all_provider_calls_for_allowed_user = _as_bool(self.all_provider_calls_for_allowed_user, True)
        self.scenario_groups_covered = [str(item) for item in _as_list(self.scenario_groups_covered)]
        self.quality_micro_shift_gate_passed = _as_bool(self.quality_micro_shift_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "execution_performed": self.execution_performed,
            "target_operator_count": self.target_operator_count,
            "scenario_count": self.scenario_count,
            "provider_calls_total": self.provider_calls_total,
            "pilot_apply_count": self.pilot_apply_count,
            "all_provider_calls_for_allowed_user": self.all_provider_calls_for_allowed_user,
            "scenario_groups_covered": list(self.scenario_groups_covered),
            "quality_micro_shift_gate_passed": self.quality_micro_shift_gate_passed,
        }


@dataclass
class ProviderBudgetGate:
    schema_version: str = "diagnostic_center_controlled_rollout_provider_budget_gate_v1"
    prd_id: str = "PRD-046.1.31"
    provider_call_budget_max: int = 12
    provider_calls_total: int = 0
    provider_budget_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_provider_budget_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.provider_call_budget_max = _as_int(self.provider_call_budget_max, 12)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.provider_budget_gate_passed = _as_bool(self.provider_budget_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "provider_call_budget_max": self.provider_call_budget_max,
            "provider_calls_total": self.provider_calls_total,
            "provider_budget_gate_passed": self.provider_budget_gate_passed,
        }


@dataclass
class NormalUserNoEffectGate:
    schema_version: str = "diagnostic_center_controlled_rollout_normal_user_no_effect_gate_v1"
    prd_id: str = "PRD-046.1.31"
    normal_user_control_count: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_calls: int = 0
    normal_user_prompt_delta_count: int = 0
    normal_user_final_answer_changed_by_rollout_count: int = 0
    gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_normal_user_no_effect_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_calls = _as_int(self.normal_user_provider_calls, 0)
        self.normal_user_prompt_delta_count = _as_int(self.normal_user_prompt_delta_count, 0)
        self.normal_user_final_answer_changed_by_rollout_count = _as_int(
            self.normal_user_final_answer_changed_by_rollout_count,
            0,
        )
        self.gate_passed = _as_bool(self.gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_calls": self.normal_user_provider_calls,
            "normal_user_prompt_delta_count": self.normal_user_prompt_delta_count,
            "normal_user_final_answer_changed_by_rollout_count": self.normal_user_final_answer_changed_by_rollout_count,
            "gate_passed": self.gate_passed,
        }


@dataclass
class QualityMicroShiftGate:
    schema_version: str = "diagnostic_center_controlled_rollout_quality_micro_shift_gate_v1"
    prd_id: str = "PRD-046.1.31"
    scenario_count: int = 0
    micro_shift_present_rate: float = 0.0
    forbidden_moves_violation_count: int = 0
    state_boundary_violation_count: int = 0
    thread_continuity_hard_fail_count: int = 0
    candidate_weaker_than_baseline_count: int = 0
    gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_quality_micro_shift_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.micro_shift_present_rate = _as_float(self.micro_shift_present_rate, 0.0)
        self.forbidden_moves_violation_count = _as_int(self.forbidden_moves_violation_count, 0)
        self.state_boundary_violation_count = _as_int(self.state_boundary_violation_count, 0)
        self.thread_continuity_hard_fail_count = _as_int(self.thread_continuity_hard_fail_count, 0)
        self.candidate_weaker_than_baseline_count = _as_int(self.candidate_weaker_than_baseline_count, 0)
        self.gate_passed = _as_bool(self.gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "scenario_count": self.scenario_count,
            "micro_shift_present_rate": self.micro_shift_present_rate,
            "forbidden_moves_violation_count": self.forbidden_moves_violation_count,
            "state_boundary_violation_count": self.state_boundary_violation_count,
            "thread_continuity_hard_fail_count": self.thread_continuity_hard_fail_count,
            "candidate_weaker_than_baseline_count": self.candidate_weaker_than_baseline_count,
            "gate_passed": self.gate_passed,
        }


@dataclass
class SafetyKBBoundaryGate:
    schema_version: str = "diagnostic_center_controlled_rollout_safety_kb_boundary_gate_v1"
    prd_id: str = "PRD-046.1.31"
    raw_kb_text_exposure_count: int = 0
    raw_provider_payload_exposure_count: int = 0
    authority_citation_count: int = 0
    direct_book_quote_count: int = 0
    internal_only_exposed_to_writer_count: int = 0
    practice_suggestion_policy_violation_count: int = 0
    governance_authority_mutation_count: int = 0
    gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_safety_kb_boundary_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.raw_kb_text_exposure_count = _as_int(self.raw_kb_text_exposure_count, 0)
        self.raw_provider_payload_exposure_count = _as_int(self.raw_provider_payload_exposure_count, 0)
        self.authority_citation_count = _as_int(self.authority_citation_count, 0)
        self.direct_book_quote_count = _as_int(self.direct_book_quote_count, 0)
        self.internal_only_exposed_to_writer_count = _as_int(self.internal_only_exposed_to_writer_count, 0)
        self.practice_suggestion_policy_violation_count = _as_int(self.practice_suggestion_policy_violation_count, 0)
        self.governance_authority_mutation_count = _as_int(self.governance_authority_mutation_count, 0)
        self.gate_passed = _as_bool(self.gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "raw_kb_text_exposure_count": self.raw_kb_text_exposure_count,
            "raw_provider_payload_exposure_count": self.raw_provider_payload_exposure_count,
            "authority_citation_count": self.authority_citation_count,
            "direct_book_quote_count": self.direct_book_quote_count,
            "internal_only_exposed_to_writer_count": self.internal_only_exposed_to_writer_count,
            "practice_suggestion_policy_violation_count": self.practice_suggestion_policy_violation_count,
            "governance_authority_mutation_count": self.governance_authority_mutation_count,
            "gate_passed": self.gate_passed,
        }


@dataclass
class TraceProviderSanitizationGate:
    schema_version: str = "diagnostic_center_controlled_rollout_trace_provider_sanitization_gate_v1"
    prd_id: str = "PRD-046.1.31"
    contains_raw_private_logs: bool = False
    contains_raw_provider_payload: bool = False
    contains_secret_like_values: bool = False
    contains_env_values: bool = False
    contains_raw_content_full: bool = False
    contains_user_private_identifier: bool = False
    contains_nul_char: bool = False
    contains_mojibake: bool = False
    utf8_clean: bool = True
    json_parseable: bool = True
    gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_trace_provider_sanitization_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.contains_raw_private_logs = _as_bool(self.contains_raw_private_logs, False)
        self.contains_raw_provider_payload = _as_bool(self.contains_raw_provider_payload, False)
        self.contains_secret_like_values = _as_bool(self.contains_secret_like_values, False)
        self.contains_env_values = _as_bool(self.contains_env_values, False)
        self.contains_raw_content_full = _as_bool(self.contains_raw_content_full, False)
        self.contains_user_private_identifier = _as_bool(self.contains_user_private_identifier, False)
        self.contains_nul_char = _as_bool(self.contains_nul_char, False)
        self.contains_mojibake = _as_bool(self.contains_mojibake, False)
        self.utf8_clean = _as_bool(self.utf8_clean, True)
        self.json_parseable = _as_bool(self.json_parseable, True)
        self.gate_passed = _as_bool(self.gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "contains_raw_private_logs": self.contains_raw_private_logs,
            "contains_raw_provider_payload": self.contains_raw_provider_payload,
            "contains_secret_like_values": self.contains_secret_like_values,
            "contains_env_values": self.contains_env_values,
            "contains_raw_content_full": self.contains_raw_content_full,
            "contains_user_private_identifier": self.contains_user_private_identifier,
            "contains_nul_char": self.contains_nul_char,
            "contains_mojibake": self.contains_mojibake,
            "utf8_clean": self.utf8_clean,
            "json_parseable": self.json_parseable,
            "gate_passed": self.gate_passed,
        }


@dataclass
class RollbackProof:
    schema_version: str = "diagnostic_center_controlled_rollout_rollback_proof_v1"
    prd_id: str = "PRD-046.1.31"
    rollback_precheck_passed: bool = False
    force_disabled_path_available: bool = False
    rollback_postcheck_passed: bool = False
    stale_apply_after_force_disabled_count: int = 0
    gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_rollback_proof_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.rollback_precheck_passed = _as_bool(self.rollback_precheck_passed, False)
        self.force_disabled_path_available = _as_bool(self.force_disabled_path_available, False)
        self.rollback_postcheck_passed = _as_bool(self.rollback_postcheck_passed, False)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0)
        self.gate_passed = _as_bool(self.gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "rollback_precheck_passed": self.rollback_precheck_passed,
            "force_disabled_path_available": self.force_disabled_path_available,
            "rollback_postcheck_passed": self.rollback_postcheck_passed,
            "stale_apply_after_force_disabled_count": self.stale_apply_after_force_disabled_count,
            "gate_passed": self.gate_passed,
        }


@dataclass
class BotDBStabilityGate:
    schema_version: str = "diagnostic_center_controlled_rollout_botdb_stability_gate_v1"
    prd_id: str = "PRD-046.1.31"
    botdb_live_reachable: bool = False
    dashboard_chroma_status: str = ""
    dashboard_chroma_count: int = -1
    registry_source_count: int = -1
    query_endpoint_status: int = 0
    semantic_fallback_used: bool = True
    botdb_circuit_open: bool = True
    gate_passed: bool = False
    blocker_reason: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_botdb_stability_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.botdb_live_reachable = _as_bool(self.botdb_live_reachable, False)
        self.dashboard_chroma_status = _as_str(self.dashboard_chroma_status, "")
        self.dashboard_chroma_count = _as_int(self.dashboard_chroma_count, -1)
        self.registry_source_count = _as_int(self.registry_source_count, -1)
        self.query_endpoint_status = _as_int(self.query_endpoint_status, 0)
        self.semantic_fallback_used = _as_bool(self.semantic_fallback_used, True)
        self.botdb_circuit_open = _as_bool(self.botdb_circuit_open, True)
        self.gate_passed = _as_bool(self.gate_passed, False)
        self.blocker_reason = _as_str(self.blocker_reason, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "botdb_live_reachable": self.botdb_live_reachable,
            "dashboard_chroma_status": self.dashboard_chroma_status,
            "dashboard_chroma_count": self.dashboard_chroma_count,
            "registry_source_count": self.registry_source_count,
            "query_endpoint_status": self.query_endpoint_status,
            "semantic_fallback_used": self.semantic_fallback_used,
            "botdb_circuit_open": self.botdb_circuit_open,
            "gate_passed": self.gate_passed,
            "blocker_reason": self.blocker_reason,
        }


@dataclass
class NoMutationProof:
    schema_version: str = "diagnostic_center_controlled_rollout_no_mutation_proof_v1"
    prd_id: str = "PRD-046.1.31"
    all_blocks_merged_mutated: bool = False
    registry_mutated: bool = False
    config_mutated: bool = False
    runtime_defaults_changed: bool = False
    production_data_mutated: bool = False
    chroma_reindex_performed: bool = False
    kb_governance_authority_mutated: bool = False
    no_mutation_proof_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_no_mutation_proof_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.all_blocks_merged_mutated = _as_bool(self.all_blocks_merged_mutated, False)
        self.registry_mutated = _as_bool(self.registry_mutated, False)
        self.config_mutated = _as_bool(self.config_mutated, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.chroma_reindex_performed = _as_bool(self.chroma_reindex_performed, False)
        self.kb_governance_authority_mutated = _as_bool(self.kb_governance_authority_mutated, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "all_blocks_merged_mutated": self.all_blocks_merged_mutated,
            "registry_mutated": self.registry_mutated,
            "config_mutated": self.config_mutated,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "production_data_mutated": self.production_data_mutated,
            "chroma_reindex_performed": self.chroma_reindex_performed,
            "kb_governance_authority_mutated": self.kb_governance_authority_mutated,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
        }


@dataclass
class ArtifactHygieneGate:
    schema_version: str = "diagnostic_center_controlled_rollout_artifact_hygiene_gate_v1"
    prd_id: str = "PRD-046.1.31"
    utf8_decode_error_count: int = 0
    nul_byte_file_count: int = 0
    json_parse_error_count: int = 0
    raw_private_log_count: int = 0
    gate_passed: bool = False
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_artifact_hygiene_gate_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.utf8_decode_error_count = _as_int(self.utf8_decode_error_count, 0)
        self.nul_byte_file_count = _as_int(self.nul_byte_file_count, 0)
        self.json_parse_error_count = _as_int(self.json_parse_error_count, 0)
        self.raw_private_log_count = _as_int(self.raw_private_log_count, 0)
        self.gate_passed = _as_bool(self.gate_passed, False)
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.blockers = [str(item) for item in _as_list(self.blockers)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "utf8_decode_error_count": self.utf8_decode_error_count,
            "nul_byte_file_count": self.nul_byte_file_count,
            "json_parse_error_count": self.json_parse_error_count,
            "raw_private_log_count": self.raw_private_log_count,
            "gate_passed": self.gate_passed,
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
        }


@dataclass
class ControlledRolloutDecision:
    schema_version: str = "diagnostic_center_controlled_rollout_decision_v1"
    prd_id: str = "PRD-046.1.31"
    final_status: str = "blocked"
    decision: str = "blocked_by_source_gate"
    source_gate_passed: bool = False
    execution_performed: bool = False
    target_operator_count: int = 0
    scenario_count: int = 0
    provider_calls_total: int = 0
    provider_budget_gate_passed: bool = False
    normal_user_control_count: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_calls: int = 0
    rollback_gate_passed: bool = False
    hard_stop_triggered: bool = True
    safety_kb_boundary_gate_passed: bool = False
    trace_provider_sanitization_gate_passed: bool = False
    botdb_stability_gate_passed: bool = False
    quality_micro_shift_gate_passed: bool = False
    no_mutation_proof_passed: bool = False
    artifact_encoding_hygiene_passed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    next_prd_recommendation: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.31")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_by_source_gate")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.execution_performed = _as_bool(self.execution_performed, False)
        self.target_operator_count = _as_int(self.target_operator_count, 0)
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.provider_budget_gate_passed = _as_bool(self.provider_budget_gate_passed, False)
        self.normal_user_control_count = _as_int(self.normal_user_control_count, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_calls = _as_int(self.normal_user_provider_calls, 0)
        self.rollback_gate_passed = _as_bool(self.rollback_gate_passed, False)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, True)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)
        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, False)
        self.botdb_stability_gate_passed = _as_bool(self.botdb_stability_gate_passed, False)
        self.quality_micro_shift_gate_passed = _as_bool(self.quality_micro_shift_gate_passed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.next_prd_recommendation = _as_str(self.next_prd_recommendation, "")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "execution_performed": self.execution_performed,
            "target_operator_count": self.target_operator_count,
            "scenario_count": self.scenario_count,
            "provider_calls_total": self.provider_calls_total,
            "provider_budget_gate_passed": self.provider_budget_gate_passed,
            "normal_user_control_count": self.normal_user_control_count,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_calls": self.normal_user_provider_calls,
            "rollback_gate_passed": self.rollback_gate_passed,
            "hard_stop_triggered": self.hard_stop_triggered,
            "safety_kb_boundary_gate_passed": self.safety_kb_boundary_gate_passed,
            "trace_provider_sanitization_gate_passed": self.trace_provider_sanitization_gate_passed,
            "botdb_stability_gate_passed": self.botdb_stability_gate_passed,
            "quality_micro_shift_gate_passed": self.quality_micro_shift_gate_passed,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "next_prd_recommendation": self.next_prd_recommendation,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


__all__ = [
    "ControlledRolloutSourceGate",
    "ControlledRolloutCohortPolicy",
    "ControlledRolloutPreflight",
    "ControlledRolloutExecutionManifest",
    "ControlledRolloutExecutionResult",
    "ProviderBudgetGate",
    "NormalUserNoEffectGate",
    "QualityMicroShiftGate",
    "SafetyKBBoundaryGate",
    "TraceProviderSanitizationGate",
    "RollbackProof",
    "BotDBStabilityGate",
    "NoMutationProof",
    "ArtifactHygieneGate",
    "ControlledRolloutDecision",
]
