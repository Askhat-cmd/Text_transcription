"""Contracts for PRD-046.1.33 limited activation readiness gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.33"
SOURCE_PRD_ID = "PRD-046.1.32"


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
class ReadinessGateInput:
    schema_version: str = "diagnostic_center_limited_activation_readiness_input_v1"
    prd_id: str = PRD_ID
    source_prd_id: str = SOURCE_PRD_ID
    strict: bool = True
    admin_base_url: str = "http://localhost:8003"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_readiness_input_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.source_prd_id = _as_str(self.source_prd_id, SOURCE_PRD_ID)
        self.strict = _as_bool(self.strict, True)
        self.admin_base_url = _as_str(self.admin_base_url, "http://localhost:8003")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "source_prd_id": self.source_prd_id,
            "strict": self.strict,
            "admin_base_url": self.admin_base_url,
        }


@dataclass
class SourceEvidenceGate:
    schema_version: str = "diagnostic_center_limited_activation_source_gate_v1"
    prd_id: str = PRD_ID
    source_prd_id: str = SOURCE_PRD_ID
    source_artifacts_present: bool = False
    source_final_status: str = "failed"
    source_decision: str = "stop_before_activation_readiness"
    source_blockers_count: int = 1
    source_warnings_count: int = 0
    warnings_non_blocking: bool = False
    source_no_mutation_passed: bool = False
    source_docs_synced: bool = False
    source_allows_readiness_prd: bool = False
    source_allows_execution: bool = False
    source_allows_broad_rollout: bool = False
    source_allows_normal_user_activation: bool = False
    source_allows_production_ready: bool = False
    missing_source_artifact_count: int = 0
    source_parse_error_count: int = 0
    source_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_source_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.source_prd_id = _as_str(self.source_prd_id, SOURCE_PRD_ID)
        self.source_artifacts_present = _as_bool(self.source_artifacts_present, False)
        self.source_final_status = _as_str(self.source_final_status, "failed")
        self.source_decision = _as_str(self.source_decision, "stop_before_activation_readiness")
        self.source_blockers_count = _as_int(self.source_blockers_count, 1)
        self.source_warnings_count = _as_int(self.source_warnings_count, 0)
        self.warnings_non_blocking = _as_bool(self.warnings_non_blocking, False)
        self.source_no_mutation_passed = _as_bool(self.source_no_mutation_passed, False)
        self.source_docs_synced = _as_bool(self.source_docs_synced, False)
        self.source_allows_readiness_prd = _as_bool(self.source_allows_readiness_prd, False)
        self.source_allows_execution = _as_bool(self.source_allows_execution, False)
        self.source_allows_broad_rollout = _as_bool(self.source_allows_broad_rollout, False)
        self.source_allows_normal_user_activation = _as_bool(self.source_allows_normal_user_activation, False)
        self.source_allows_production_ready = _as_bool(self.source_allows_production_ready, False)
        self.missing_source_artifact_count = _as_int(self.missing_source_artifact_count, 0)
        self.source_parse_error_count = _as_int(self.source_parse_error_count, 0)
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class LiveDependencyGate:
    schema_version: str = "diagnostic_center_limited_activation_live_dependency_gate_v1"
    prd_id: str = PRD_ID
    botdb_live_status: str = "blocked_admin_api_unavailable"
    status_endpoint_ok: bool = False
    registry_endpoint_ok: bool = False
    dashboard_endpoint_ok: bool = False
    focus_source_present: bool = False
    focus_source_id: str = ""
    registry_source_count: int = -1
    blocks_count: int = -1
    chroma_count: int = -1
    query_path_ready: bool = False
    semantic_fallback_used: bool = True
    botdb_circuit_open: bool = True
    live_dependency_gate_passed: bool = False
    checks: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_live_dependency_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.botdb_live_status = _as_str(self.botdb_live_status, "blocked_admin_api_unavailable")
        self.status_endpoint_ok = _as_bool(self.status_endpoint_ok, False)
        self.registry_endpoint_ok = _as_bool(self.registry_endpoint_ok, False)
        self.dashboard_endpoint_ok = _as_bool(self.dashboard_endpoint_ok, False)
        self.focus_source_present = _as_bool(self.focus_source_present, False)
        self.focus_source_id = _as_str(self.focus_source_id, "")
        self.registry_source_count = _as_int(self.registry_source_count, -1)
        self.blocks_count = _as_int(self.blocks_count, -1)
        self.chroma_count = _as_int(self.chroma_count, -1)
        self.query_path_ready = _as_bool(self.query_path_ready, False)
        self.semantic_fallback_used = _as_bool(self.semantic_fallback_used, True)
        self.botdb_circuit_open = _as_bool(self.botdb_circuit_open, True)
        self.live_dependency_gate_passed = _as_bool(self.live_dependency_gate_passed, False)
        self.checks = _safe_dict(self.checks)

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["checks"] = dict(self.checks)
        return payload


@dataclass
class RuntimeBoundaryGate:
    schema_version: str = "diagnostic_center_limited_activation_runtime_boundary_gate_v1"
    prd_id: str = PRD_ID
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    writer_contract_changed_for_normal_users: bool = False
    writer_prompt_changed_for_normal_users: bool = False
    final_answer_path_changed_for_normal_users: bool = False
    runtime_defaults_changed: bool = False
    diagnostic_center_is_internal_map_layer: bool = True
    writer_remains_user_facing_agent: bool = True
    diagnostic_center_does_not_generate_final_answer: bool = True
    kb_not_used_as_direct_quote_source: bool = True
    runtime_boundary_gate_passed: bool = True

    def __post_init__(self) -> None:
        for key in list(self.__dict__.keys()):
            if key in {"schema_version", "prd_id"}:
                continue
            setattr(self, key, _as_bool(getattr(self, key), getattr(RuntimeBoundaryGate, key)))
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_runtime_boundary_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NormalUserBoundaryGate:
    schema_version: str = "diagnostic_center_limited_activation_normal_user_boundary_gate_v1"
    prd_id: str = PRD_ID
    scenarios_checked: list[str] = field(default_factory=list)
    normal_user_apply_effect_count: int = 0
    normal_user_provider_call_count: int = 0
    normal_user_writer_prompt_delta_count: int = 0
    normal_user_final_answer_path_delta_count: int = 0
    normal_user_trace_private_leak_count: int = 0
    normal_user_boundary_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_normal_user_boundary_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.scenarios_checked = [str(item) for item in self.scenarios_checked]
        self.normal_user_apply_effect_count = _as_int(self.normal_user_apply_effect_count, 0)
        self.normal_user_provider_call_count = _as_int(self.normal_user_provider_call_count, 0)
        self.normal_user_writer_prompt_delta_count = _as_int(self.normal_user_writer_prompt_delta_count, 0)
        self.normal_user_final_answer_path_delta_count = _as_int(self.normal_user_final_answer_path_delta_count, 0)
        self.normal_user_trace_private_leak_count = _as_int(self.normal_user_trace_private_leak_count, 0)
        self.normal_user_boundary_gate_passed = _as_bool(self.normal_user_boundary_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class AllowlistPolicyGate:
    schema_version: str = "diagnostic_center_limited_activation_allowlist_policy_gate_v1"
    prd_id: str = PRD_ID
    allowlist_required: bool = True
    allowlist_scope: str = "explicit_users_only"
    max_live_users_recommended: int = 3
    activation_window_required: bool = True
    provider_budget_required: bool = True
    hard_stop_required: bool = True
    rollback_first_required: bool = True
    normal_user_controls_required: bool = True
    raw_payload_commit_forbidden: bool = True
    allowlist_policy_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_allowlist_policy_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.allowlist_required = _as_bool(self.allowlist_required, True)
        self.allowlist_scope = _as_str(self.allowlist_scope, "explicit_users_only")
        self.max_live_users_recommended = _as_int(self.max_live_users_recommended, 3)
        self.activation_window_required = _as_bool(self.activation_window_required, True)
        self.provider_budget_required = _as_bool(self.provider_budget_required, True)
        self.hard_stop_required = _as_bool(self.hard_stop_required, True)
        self.rollback_first_required = _as_bool(self.rollback_first_required, True)
        self.normal_user_controls_required = _as_bool(self.normal_user_controls_required, True)
        self.raw_payload_commit_forbidden = _as_bool(self.raw_payload_commit_forbidden, True)
        self.allowlist_policy_gate_passed = _as_bool(self.allowlist_policy_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RollbackHardStopGate:
    schema_version: str = "diagnostic_center_limited_activation_rollback_hard_stop_gate_v1"
    prd_id: str = PRD_ID
    rollback_controls_present: bool = True
    rollback_priority_force_disabled: bool = True
    hard_stop_criteria_present: bool = True
    hard_stop_criteria_complete: bool = True
    future_execution_without_rollback_blocked: bool = True
    rollback_hard_stop_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_rollback_hard_stop_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.rollback_controls_present = _as_bool(self.rollback_controls_present, True)
        self.rollback_priority_force_disabled = _as_bool(self.rollback_priority_force_disabled, True)
        self.hard_stop_criteria_present = _as_bool(self.hard_stop_criteria_present, True)
        self.hard_stop_criteria_complete = _as_bool(self.hard_stop_criteria_complete, True)
        self.future_execution_without_rollback_blocked = _as_bool(self.future_execution_without_rollback_blocked, True)
        self.rollback_hard_stop_gate_passed = _as_bool(self.rollback_hard_stop_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class SafetyKBBoundaryGate:
    schema_version: str = "diagnostic_center_limited_activation_safety_kb_boundary_gate_v1"
    prd_id: str = PRD_ID
    raw_content_full_exposure_count: int = 0
    internal_only_exposure_count: int = 0
    authority_citation_count: int = 0
    practice_policy_violation_count: int = 0
    safety_kb_boundary_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_safety_kb_boundary_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.raw_content_full_exposure_count = _as_int(self.raw_content_full_exposure_count, 0)
        self.internal_only_exposure_count = _as_int(self.internal_only_exposure_count, 0)
        self.authority_citation_count = _as_int(self.authority_citation_count, 0)
        self.practice_policy_violation_count = _as_int(self.practice_policy_violation_count, 0)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TraceProviderSanitizationGate:
    schema_version: str = "diagnostic_center_limited_activation_trace_provider_sanitization_gate_v1"
    prd_id: str = PRD_ID
    raw_provider_payload_committed: bool = False
    raw_private_logs_committed: bool = False
    secrets_committed: bool = False
    env_committed: bool = False
    trace_contains_only_sanitized_provider_summary: bool = True
    trace_contains_no_full_user_private_payload: bool = True
    trace_provider_sanitization_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_trace_provider_sanitization_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.raw_private_logs_committed = _as_bool(self.raw_private_logs_committed, False)
        self.secrets_committed = _as_bool(self.secrets_committed, False)
        self.env_committed = _as_bool(self.env_committed, False)
        self.trace_contains_only_sanitized_provider_summary = _as_bool(self.trace_contains_only_sanitized_provider_summary, True)
        self.trace_contains_no_full_user_private_payload = _as_bool(self.trace_contains_no_full_user_private_payload, True)
        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RuntimeDefaultsGate:
    schema_version: str = "diagnostic_center_limited_activation_runtime_defaults_gate_v1"
    prd_id: str = PRD_ID
    runtime_defaults_changed: bool = False
    broad_rollout_default: bool = False
    normal_user_activation_default: bool = False
    force_disabled_priority_preserved: bool = True
    allowlisted_activation_default: bool = False
    disabled_until_next_prd: bool = True
    runtime_defaults_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_runtime_defaults_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.broad_rollout_default = _as_bool(self.broad_rollout_default, False)
        self.normal_user_activation_default = _as_bool(self.normal_user_activation_default, False)
        self.force_disabled_priority_preserved = _as_bool(self.force_disabled_priority_preserved, True)
        self.allowlisted_activation_default = _as_bool(self.allowlisted_activation_default, False)
        self.disabled_until_next_prd = _as_bool(self.disabled_until_next_prd, True)
        self.runtime_defaults_gate_passed = _as_bool(self.runtime_defaults_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ProviderBudgetPolicyGate:
    schema_version: str = "diagnostic_center_limited_activation_provider_budget_policy_gate_v1"
    prd_id: str = PRD_ID
    provider_called_by_prd_046_1_33: bool = False
    provider_execution_performed: bool = False
    future_provider_budget_required: bool = True
    future_budget_cap_recommended: bool = True
    future_budget_cap_value_defined: bool = True
    max_provider_calls_recommended: int = 10
    provider_budget_policy_gate_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_provider_budget_policy_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.provider_called_by_prd_046_1_33 = _as_bool(self.provider_called_by_prd_046_1_33, False)
        self.provider_execution_performed = _as_bool(self.provider_execution_performed, False)
        self.future_provider_budget_required = _as_bool(self.future_provider_budget_required, True)
        self.future_budget_cap_recommended = _as_bool(self.future_budget_cap_recommended, True)
        self.future_budget_cap_value_defined = _as_bool(self.future_budget_cap_value_defined, True)
        self.max_provider_calls_recommended = _as_int(self.max_provider_calls_recommended, 10)
        self.provider_budget_policy_gate_passed = _as_bool(self.provider_budget_policy_gate_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NoMutationProof:
    schema_version: str = "diagnostic_center_limited_activation_no_mutation_proof_v1"
    prd_id: str = PRD_ID
    production_data_mutated: bool = False
    runtime_defaults_changed: bool = False
    kb_registry_chroma_config_mutated: bool = False
    chroma_reindex_performed: bool = False
    provider_called: bool = False
    new_runtime_execution_performed: bool = False
    raw_provider_payload_committed: bool = False
    no_mutation_proof_passed: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_no_mutation_proof_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.kb_registry_chroma_config_mutated = _as_bool(self.kb_registry_chroma_config_mutated, False)
        self.chroma_reindex_performed = _as_bool(self.chroma_reindex_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.new_runtime_execution_performed = _as_bool(self.new_runtime_execution_performed, False)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class DocsConsistencyGate:
    schema_version: str = "diagnostic_center_limited_activation_docs_consistency_gate_v1"
    prd_id: str = PRD_ID
    project_state_synced: bool = False
    roadmap_synced: bool = False
    prd_index_synced: bool = False
    decisions_synced: bool = False
    stale_next_prd_reference_count: int = 0
    duplicate_roadmap_next_item_count: int = 0
    docs_consistency_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_docs_consistency_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.project_state_synced = _as_bool(self.project_state_synced, False)
        self.roadmap_synced = _as_bool(self.roadmap_synced, False)
        self.prd_index_synced = _as_bool(self.prd_index_synced, False)
        self.decisions_synced = _as_bool(self.decisions_synced, False)
        self.stale_next_prd_reference_count = _as_int(self.stale_next_prd_reference_count, 0)
        self.duplicate_roadmap_next_item_count = _as_int(self.duplicate_roadmap_next_item_count, 0)
        self.docs_consistency_gate_passed = _as_bool(self.docs_consistency_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NextPrdRecommendation:
    schema_version: str = "diagnostic_center_limited_activation_next_prd_recommendation_v1"
    prd_id: str = PRD_ID
    next_prd: str = "PRD-046.1.33-HF1 - blocker fix"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_next_prd_recommendation_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.next_prd = _as_str(self.next_prd, "PRD-046.1.33-HF1 - blocker fix")

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ReadinessScorecard:
    schema_version: str = "diagnostic_center_limited_activation_readiness_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "failed"
    decision: str = "stop_runtime_activation_path"
    source_gate: str = "failed"
    live_dependency_gate: str = "failed"
    runtime_boundary_gate: str = "failed"
    normal_user_boundary_gate: str = "failed"
    allowlist_policy_gate: str = "failed"
    rollback_hard_stop_gate: str = "failed"
    safety_kb_boundary_gate: str = "failed"
    trace_provider_sanitization_gate: str = "failed"
    runtime_defaults_gate: str = "failed"
    provider_budget_policy_gate: str = "failed"
    no_mutation_proof: str = "failed"
    artifact_encoding_hygiene: str = "failed"
    docs_consistency_gate: str = "failed"
    new_execution_performed: bool = False
    provider_called: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    next_prd: str = "PRD-046.1.33-HF1 - blocker fix"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_readiness_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "stop_runtime_activation_path")
        self.next_prd = _as_str(self.next_prd, "PRD-046.1.33-HF1 - blocker fix")
        self.new_execution_performed = _as_bool(self.new_execution_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ReadinessGateResult:
    schema_version: str = "diagnostic_center_limited_activation_readiness_result_v1"
    prd_id: str = PRD_ID
    final_status: str = "failed"
    decision: str = "stop_runtime_activation_path"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_limited_activation_readiness_result_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "stop_runtime_activation_path")
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "ReadinessGateInput",
    "ReadinessGateResult",
    "SourceEvidenceGate",
    "LiveDependencyGate",
    "RuntimeBoundaryGate",
    "NormalUserBoundaryGate",
    "AllowlistPolicyGate",
    "RollbackHardStopGate",
    "SafetyKBBoundaryGate",
    "TraceProviderSanitizationGate",
    "RuntimeDefaultsGate",
    "ProviderBudgetPolicyGate",
    "NoMutationProof",
    "DocsConsistencyGate",
    "ReadinessScorecard",
    "NextPrdRecommendation",
]
