"""Contracts for PRD-046.1.34 creator-only live activation gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.34"
SOURCE_PRD_ID = "PRD-046.1.33"


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
class SourceGate:
    schema_version: str = "diagnostic_center_creator_live_source_gate_v1"
    prd_id: str = PRD_ID
    source_prd_id: str = SOURCE_PRD_ID
    source_artifacts_present: bool = False
    source_final_status: str = "failed"
    source_decision: str = "blocked"
    source_blockers_count: int = 1
    source_warnings_count: int = 0
    source_no_mutation_passed: bool = False
    source_docs_consistency_passed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    missing_source_artifact_count: int = 0
    source_parse_error_count: int = 0
    source_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_source_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.source_prd_id = _as_str(self.source_prd_id, SOURCE_PRD_ID)
        self.source_artifacts_present = _as_bool(self.source_artifacts_present, False)
        self.source_final_status = _as_str(self.source_final_status, "failed")
        self.source_decision = _as_str(self.source_decision, "blocked")
        self.source_blockers_count = _as_int(self.source_blockers_count, 1)
        self.source_warnings_count = _as_int(self.source_warnings_count, 0)
        self.source_no_mutation_passed = _as_bool(self.source_no_mutation_passed, False)
        self.source_docs_consistency_passed = _as_bool(self.source_docs_consistency_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.missing_source_artifact_count = _as_int(self.missing_source_artifact_count, 0)
        self.source_parse_error_count = _as_int(self.source_parse_error_count, 0)
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class CreatorIdentityGate:
    schema_version: str = "diagnostic_center_creator_identity_gate_v1"
    prd_id: str = PRD_ID
    creator_identity_ready: bool = False
    creator_identity_value: str = ""
    creator_identity_source: str = "missing"
    creator_identity_blocked_reason: str = "creator_identity_blocked_missing_user_id"
    creator_identity_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_identity_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.creator_identity_ready = _as_bool(self.creator_identity_ready, False)
        self.creator_identity_value = _as_str(self.creator_identity_value, "")
        self.creator_identity_source = _as_str(self.creator_identity_source, "missing")
        self.creator_identity_blocked_reason = _as_str(self.creator_identity_blocked_reason, "creator_identity_blocked_missing_user_id")
        self.creator_identity_gate_passed = _as_bool(self.creator_identity_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class AdminRuntimeControlsGate:
    schema_version: str = "diagnostic_center_admin_runtime_controls_gate_v1"
    prd_id: str = PRD_ID
    runtime_tab_present: bool = False
    diagnostic_center_block_present: bool = False
    runtime_mode_supported: list[str] = field(default_factory=list)
    runtime_mode_effective: str = "disabled"
    force_disabled_toggle_present: bool = False
    all_users_control_locked: bool = True
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    admin_runtime_controls_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_admin_runtime_controls_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.runtime_tab_present = _as_bool(self.runtime_tab_present, False)
        self.diagnostic_center_block_present = _as_bool(self.diagnostic_center_block_present, False)
        self.runtime_mode_supported = [str(item) for item in _safe_list(self.runtime_mode_supported)]
        self.runtime_mode_effective = _as_str(self.runtime_mode_effective, "disabled")
        self.force_disabled_toggle_present = _as_bool(self.force_disabled_toggle_present, False)
        self.all_users_control_locked = _as_bool(self.all_users_control_locked, True)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.admin_runtime_controls_gate_passed = _as_bool(self.admin_runtime_controls_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class WebChatCreatorLiveSmoke:
    schema_version: str = "diagnostic_center_creator_web_chat_live_smoke_v1"
    prd_id: str = PRD_ID
    creator_identity_ready: bool = False
    web_chat_reachable: bool = False
    message_sent: bool = False
    answer_received: bool = False
    diagnostic_center_mode: str = "disabled"
    creator_path_active: bool = False
    normal_user_path_unchanged: bool = False
    trace_saved: bool = False
    monitor_visible: bool = False
    raw_provider_payload_committed: bool = False
    raw_private_logs_committed: bool = False
    smoke_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_web_chat_live_smoke_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.creator_identity_ready = _as_bool(self.creator_identity_ready, False)
        self.web_chat_reachable = _as_bool(self.web_chat_reachable, False)
        self.message_sent = _as_bool(self.message_sent, False)
        self.answer_received = _as_bool(self.answer_received, False)
        self.diagnostic_center_mode = _as_str(self.diagnostic_center_mode, "disabled")
        self.creator_path_active = _as_bool(self.creator_path_active, False)
        self.normal_user_path_unchanged = _as_bool(self.normal_user_path_unchanged, False)
        self.trace_saved = _as_bool(self.trace_saved, False)
        self.monitor_visible = _as_bool(self.monitor_visible, False)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.raw_private_logs_committed = _as_bool(self.raw_private_logs_committed, False)
        self.smoke_passed = _as_bool(self.smoke_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NormalUserNoEffectGate:
    schema_version: str = "diagnostic_center_creator_normal_user_no_effect_gate_v1"
    prd_id: str = PRD_ID
    normal_user_apply_effect_count: int = 0
    normal_user_provider_call_count: int = 0
    writer_prompt_delta_count: int = 0
    final_answer_path_delta_count: int = 0
    trace_private_leak_count: int = 0
    normal_user_no_effect_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_normal_user_no_effect_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.normal_user_apply_effect_count = _as_int(self.normal_user_apply_effect_count, 0)
        self.normal_user_provider_call_count = _as_int(self.normal_user_provider_call_count, 0)
        self.writer_prompt_delta_count = _as_int(self.writer_prompt_delta_count, 0)
        self.final_answer_path_delta_count = _as_int(self.final_answer_path_delta_count, 0)
        self.trace_private_leak_count = _as_int(self.trace_private_leak_count, 0)
        self.normal_user_no_effect_gate_passed = _as_bool(self.normal_user_no_effect_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ActiveInfluenceGate:
    schema_version: str = "diagnostic_center_creator_active_influence_gate_v1"
    prd_id: str = PRD_ID
    creator_path_active: bool = False
    writer_constraint_injected: bool = False
    forbidden_moves_controlled: bool = False
    diagnostic_center_does_not_write_final_answer: bool = True
    normal_user_path_unchanged: bool = False
    active_influence_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_active_influence_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.creator_path_active = _as_bool(self.creator_path_active, False)
        self.writer_constraint_injected = _as_bool(self.writer_constraint_injected, False)
        self.forbidden_moves_controlled = _as_bool(self.forbidden_moves_controlled, False)
        self.diagnostic_center_does_not_write_final_answer = _as_bool(self.diagnostic_center_does_not_write_final_answer, True)
        self.normal_user_path_unchanged = _as_bool(self.normal_user_path_unchanged, False)
        self.active_influence_gate_passed = _as_bool(self.active_influence_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RollbackKillSwitchGate:
    schema_version: str = "diagnostic_center_creator_rollback_kill_switch_gate_v1"
    prd_id: str = PRD_ID
    force_disabled_priority_preserved: bool = False
    rollback_ready: bool = False
    stale_apply_after_force_disabled_count: int = 0
    rollback_kill_switch_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_rollback_kill_switch_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.force_disabled_priority_preserved = _as_bool(self.force_disabled_priority_preserved, False)
        self.rollback_ready = _as_bool(self.rollback_ready, False)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0)
        self.rollback_kill_switch_gate_passed = _as_bool(self.rollback_kill_switch_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HardStopGate:
    schema_version: str = "diagnostic_center_creator_hard_stop_gate_v1"
    prd_id: str = PRD_ID
    hard_stop_triggered: bool = False
    triggered_reasons: list[str] = field(default_factory=list)
    force_disabled_after_hard_stop: bool = False
    hard_stop_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_hard_stop_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, False)
        self.triggered_reasons = [str(item) for item in _safe_list(self.triggered_reasons)]
        self.force_disabled_after_hard_stop = _as_bool(self.force_disabled_after_hard_stop, False)
        self.hard_stop_gate_passed = _as_bool(self.hard_stop_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class SafetyKBBoundaryGate:
    schema_version: str = "diagnostic_center_creator_safety_kb_boundary_gate_v1"
    prd_id: str = PRD_ID
    raw_content_full_exposure_count: int = 0
    kb_authority_quote_count: int = 0
    forbidden_practice_suggestion_count: int = 0
    safety_kb_boundary_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_safety_kb_boundary_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.raw_content_full_exposure_count = _as_int(self.raw_content_full_exposure_count, 0)
        self.kb_authority_quote_count = _as_int(self.kb_authority_quote_count, 0)
        self.forbidden_practice_suggestion_count = _as_int(self.forbidden_practice_suggestion_count, 0)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TraceProviderSanitizationGate:
    schema_version: str = "diagnostic_center_creator_trace_provider_sanitization_gate_v1"
    prd_id: str = PRD_ID
    raw_provider_payload_committed: bool = False
    raw_private_logs_committed: bool = False
    secrets_committed: bool = False
    env_committed: bool = False
    trace_sanitized_only: bool = False
    trace_provider_sanitization_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_trace_provider_sanitization_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.raw_private_logs_committed = _as_bool(self.raw_private_logs_committed, False)
        self.secrets_committed = _as_bool(self.secrets_committed, False)
        self.env_committed = _as_bool(self.env_committed, False)
        self.trace_sanitized_only = _as_bool(self.trace_sanitized_only, False)
        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TraceStorageGate:
    schema_version: str = "diagnostic_center_creator_trace_storage_gate_v1"
    prd_id: str = PRD_ID
    storage_strategy: str = "dev_jsonl_non_repo"
    gitignore_guard_present: bool = False
    runtime_traces_committed: bool = False
    sanitized_sample_present: bool = False
    trace_storage_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_trace_storage_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.storage_strategy = _as_str(self.storage_strategy, "dev_jsonl_non_repo")
        self.gitignore_guard_present = _as_bool(self.gitignore_guard_present, False)
        self.runtime_traces_committed = _as_bool(self.runtime_traces_committed, False)
        self.sanitized_sample_present = _as_bool(self.sanitized_sample_present, False)
        self.trace_storage_gate_passed = _as_bool(self.trace_storage_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class DiagnosticCenterMonitorGate:
    schema_version: str = "diagnostic_center_creator_monitor_gate_v1"
    prd_id: str = PRD_ID
    monitor_surface_present: bool = False
    last_turn_visible: bool = False
    sanitized_view_action_present: bool = False
    export_sanitized_action_present: bool = False
    monitor_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_monitor_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.monitor_surface_present = _as_bool(self.monitor_surface_present, False)
        self.last_turn_visible = _as_bool(self.last_turn_visible, False)
        self.sanitized_view_action_present = _as_bool(self.sanitized_view_action_present, False)
        self.export_sanitized_action_present = _as_bool(self.export_sanitized_action_present, False)
        self.monitor_gate_passed = _as_bool(self.monitor_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TraceClearancePolicyGate:
    schema_version: str = "diagnostic_center_creator_trace_clearance_policy_gate_v1"
    prd_id: str = PRD_ID
    clear_operations_supported: list[str] = field(default_factory=list)
    export_before_clear: bool = False
    prd_evidence_preserved: bool = False
    kb_mutated: bool = False
    raw_private_payload_committed: bool = False
    trace_clearance_policy_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_trace_clearance_policy_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.clear_operations_supported = [str(item) for item in _safe_list(self.clear_operations_supported)]
        self.export_before_clear = _as_bool(self.export_before_clear, False)
        self.prd_evidence_preserved = _as_bool(self.prd_evidence_preserved, False)
        self.kb_mutated = _as_bool(self.kb_mutated, False)
        self.raw_private_payload_committed = _as_bool(self.raw_private_payload_committed, False)
        self.trace_clearance_policy_gate_passed = _as_bool(self.trace_clearance_policy_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ProviderBudgetGate:
    schema_version: str = "diagnostic_center_creator_provider_budget_gate_v1"
    prd_id: str = PRD_ID
    max_creator_live_provider_calls: int = 8
    max_normal_user_control_provider_calls: int = 2
    max_total_provider_calls: int = 10
    creator_live_provider_calls: int = 0
    normal_user_control_provider_calls: int = 0
    total_provider_calls: int = 0
    provider_budget_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_provider_budget_gate_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.max_creator_live_provider_calls = _as_int(self.max_creator_live_provider_calls, 8)
        self.max_normal_user_control_provider_calls = _as_int(self.max_normal_user_control_provider_calls, 2)
        self.max_total_provider_calls = _as_int(self.max_total_provider_calls, 10)
        self.creator_live_provider_calls = _as_int(self.creator_live_provider_calls, 0)
        self.normal_user_control_provider_calls = _as_int(self.normal_user_control_provider_calls, 0)
        self.total_provider_calls = _as_int(self.total_provider_calls, 0)
        self.provider_budget_gate_passed = _as_bool(self.provider_budget_gate_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class NoMutationProof:
    schema_version: str = "diagnostic_center_creator_no_mutation_proof_v1"
    prd_id: str = PRD_ID
    production_data_mutated: bool = False
    runtime_defaults_changed: bool = False
    kb_registry_chroma_config_mutated: bool = False
    chroma_reindex_performed: bool = False
    raw_provider_payload_committed: bool = False
    no_mutation_proof_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_no_mutation_proof_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.kb_registry_chroma_config_mutated = _as_bool(self.kb_registry_chroma_config_mutated, False)
        self.chroma_reindex_performed = _as_bool(self.chroma_reindex_performed, False)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class DocsConsistencyGate:
    schema_version: str = "diagnostic_center_creator_docs_consistency_gate_v1"
    prd_id: str = PRD_ID
    project_state_synced: bool = False
    roadmap_synced: bool = False
    prd_index_synced: bool = False
    decisions_synced: bool = False
    stale_next_prd_reference_count: int = 0
    duplicate_roadmap_next_item_count: int = 0
    docs_consistency_gate_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_docs_consistency_gate_v1")
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
class LiveActivationScorecard:
    schema_version: str = "diagnostic_center_creator_live_activation_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "creator_live_activation_blocked_fix_required"
    source_gate: str = "blocked"
    creator_identity_gate: str = "blocked"
    admin_runtime_controls_gate: str = "blocked"
    web_chat_creator_live_smoke: str = "blocked"
    normal_user_no_effect_gate: str = "blocked"
    diagnostic_center_active_influence_gate: str = "blocked"
    rollback_kill_switch_gate: str = "blocked"
    hard_stop_gate: str = "blocked"
    safety_kb_boundary_gate: str = "blocked"
    trace_provider_sanitization_gate: str = "blocked"
    trace_storage_gate: str = "blocked"
    diagnostic_center_monitor_gate: str = "blocked"
    trace_clearance_policy_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"
    docs_consistency_gate: str = "blocked"
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False
    creator_only_active: bool = False
    unknown_normal_user_effect_count: int = 0
    runtime_defaults_changed_for_normal_users: bool = False
    kb_registry_chroma_config_mutated: bool = False
    raw_provider_payload_committed: bool = False
    raw_private_logs_committed: bool = False
    next_prd_recommendation: str = "PRD-046.1.34-HF1"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_activation_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "creator_live_activation_blocked_fix_required")
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.all_users_mode_enabled = _as_bool(self.all_users_mode_enabled, False)
        self.creator_only_active = _as_bool(self.creator_only_active, False)
        self.unknown_normal_user_effect_count = _as_int(self.unknown_normal_user_effect_count, 0)
        self.runtime_defaults_changed_for_normal_users = _as_bool(self.runtime_defaults_changed_for_normal_users, False)
        self.kb_registry_chroma_config_mutated = _as_bool(self.kb_registry_chroma_config_mutated, False)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.raw_private_logs_committed = _as_bool(self.raw_private_logs_committed, False)
        self.next_prd_recommendation = _as_str(self.next_prd_recommendation, "PRD-046.1.34-HF1")
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class LiveActivationDecision:
    schema_version: str = "diagnostic_center_creator_live_activation_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "creator_live_activation_blocked_fix_required"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_creator_live_activation_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "creator_live_activation_blocked_fix_required")
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "SourceGate",
    "CreatorIdentityGate",
    "AdminRuntimeControlsGate",
    "WebChatCreatorLiveSmoke",
    "NormalUserNoEffectGate",
    "ActiveInfluenceGate",
    "RollbackKillSwitchGate",
    "HardStopGate",
    "SafetyKBBoundaryGate",
    "TraceProviderSanitizationGate",
    "TraceStorageGate",
    "DiagnosticCenterMonitorGate",
    "TraceClearancePolicyGate",
    "ProviderBudgetGate",
    "NoMutationProof",
    "DocsConsistencyGate",
    "LiveActivationScorecard",
    "LiveActivationDecision",
]
