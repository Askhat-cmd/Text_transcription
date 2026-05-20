"""Contracts for PRD-046.1.32 controlled rollout results/rollback/quality gate."""

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


@dataclass
class ControlledRolloutResultsGateDecisionV1:
    schema_version: str = "diagnostic_center_controlled_rollout_results_gate_decision_v1"
    prd_id: str = "PRD-046.1.32"
    source_prd_id: str = "PRD-046.1.31"
    final_status: str = "failed"
    decision: str = "stop_before_activation_readiness"

    source_gate_passed: bool = False
    missing_source_artifact_count: int = 0
    source_final_status: str = "failed"
    source_decision: str = "controlled_rollout_execution_blocked"

    new_execution_performed: bool = False
    provider_called_by_results_gate: bool = False

    target_operator_count: int = 0
    scenario_count: int = 0
    provider_calls_total: int = 0
    provider_budget_gate_passed: bool = False

    normal_user_controls_total: int = 0
    normal_user_apply_count: int = 0
    normal_user_provider_calls_total: int = 0
    normal_user_no_effect_passed: bool = False

    quality_micro_shift_gate_passed: bool = False
    candidate_weaker_than_baseline_count: int = 0
    hard_fail_count: int = 0
    response_quality_regression_count: int = 0

    rollback_gate_passed: bool = False
    rollback_failure_count: int = 0
    stale_apply_after_force_disabled_count: int = 0
    hard_stop_triggered: bool = False

    safety_kb_boundary_gate_passed: bool = False
    raw_kb_text_exposure_count: int = 0
    kb_authority_violation_count: int = 0
    unsafe_practice_suggestion_count: int = 0

    trace_provider_sanitization_gate_passed: bool = False
    raw_provider_payload_committed_count: int = 0
    secret_like_value_count: int = 0
    private_log_leak_count: int = 0

    botdb_stability_gate_passed: bool = False
    botdb_query_ok: bool = False
    botdb_semantic_fallback_used: bool = True

    no_mutation_proof_passed: bool = False
    runtime_defaults_changed: bool = False
    production_data_mutated: bool = False
    kb_registry_chroma_config_mutated: bool = False

    artifact_encoding_hygiene_passed: bool = False
    utf8_decode_error_count: int = 0
    nul_byte_file_count: int = 0
    json_parse_error_count: int = 0
    replacement_char_warning_count: int = 0

    docs_consistency_passed: bool = False
    project_state_synced: bool = False
    roadmap_synced: bool = False
    prd_index_synced: bool = False
    decisions_synced: bool = False
    stale_next_prd_reference_count: int = 0
    duplicate_roadmap_next_item_count: int = 0

    next_recommended_prd: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_controlled_rollout_results_gate_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.32")
        self.source_prd_id = _as_str(self.source_prd_id, "PRD-046.1.31")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "stop_before_activation_readiness")

        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.missing_source_artifact_count = _as_int(self.missing_source_artifact_count, 0)
        self.source_final_status = _as_str(self.source_final_status, "failed")
        self.source_decision = _as_str(self.source_decision, "controlled_rollout_execution_blocked")

        self.new_execution_performed = _as_bool(self.new_execution_performed, False)
        self.provider_called_by_results_gate = _as_bool(self.provider_called_by_results_gate, False)

        self.target_operator_count = _as_int(self.target_operator_count, 0)
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.provider_calls_total = _as_int(self.provider_calls_total, 0)
        self.provider_budget_gate_passed = _as_bool(self.provider_budget_gate_passed, False)

        self.normal_user_controls_total = _as_int(self.normal_user_controls_total, 0)
        self.normal_user_apply_count = _as_int(self.normal_user_apply_count, 0)
        self.normal_user_provider_calls_total = _as_int(self.normal_user_provider_calls_total, 0)
        self.normal_user_no_effect_passed = _as_bool(self.normal_user_no_effect_passed, False)

        self.quality_micro_shift_gate_passed = _as_bool(self.quality_micro_shift_gate_passed, False)
        self.candidate_weaker_than_baseline_count = _as_int(self.candidate_weaker_than_baseline_count, 0)
        self.hard_fail_count = _as_int(self.hard_fail_count, 0)
        self.response_quality_regression_count = _as_int(self.response_quality_regression_count, 0)

        self.rollback_gate_passed = _as_bool(self.rollback_gate_passed, False)
        self.rollback_failure_count = _as_int(self.rollback_failure_count, 0)
        self.stale_apply_after_force_disabled_count = _as_int(self.stale_apply_after_force_disabled_count, 0)
        self.hard_stop_triggered = _as_bool(self.hard_stop_triggered, False)

        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)
        self.raw_kb_text_exposure_count = _as_int(self.raw_kb_text_exposure_count, 0)
        self.kb_authority_violation_count = _as_int(self.kb_authority_violation_count, 0)
        self.unsafe_practice_suggestion_count = _as_int(self.unsafe_practice_suggestion_count, 0)

        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, False)
        self.raw_provider_payload_committed_count = _as_int(self.raw_provider_payload_committed_count, 0)
        self.secret_like_value_count = _as_int(self.secret_like_value_count, 0)
        self.private_log_leak_count = _as_int(self.private_log_leak_count, 0)

        self.botdb_stability_gate_passed = _as_bool(self.botdb_stability_gate_passed, False)
        self.botdb_query_ok = _as_bool(self.botdb_query_ok, False)
        self.botdb_semantic_fallback_used = _as_bool(self.botdb_semantic_fallback_used, True)

        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.kb_registry_chroma_config_mutated = _as_bool(self.kb_registry_chroma_config_mutated, False)

        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.utf8_decode_error_count = _as_int(self.utf8_decode_error_count, 0)
        self.nul_byte_file_count = _as_int(self.nul_byte_file_count, 0)
        self.json_parse_error_count = _as_int(self.json_parse_error_count, 0)
        self.replacement_char_warning_count = _as_int(self.replacement_char_warning_count, 0)

        self.docs_consistency_passed = _as_bool(self.docs_consistency_passed, False)
        self.project_state_synced = _as_bool(self.project_state_synced, False)
        self.roadmap_synced = _as_bool(self.roadmap_synced, False)
        self.prd_index_synced = _as_bool(self.prd_index_synced, False)
        self.decisions_synced = _as_bool(self.decisions_synced, False)
        self.stale_next_prd_reference_count = _as_int(self.stale_next_prd_reference_count, 0)
        self.duplicate_roadmap_next_item_count = _as_int(self.duplicate_roadmap_next_item_count, 0)

        self.next_recommended_prd = _as_str(
            self.next_recommended_prd,
            "PRD-046.1.33 - Diagnostic Center Limited Runtime Activation Readiness / Normal-User Boundary Decision Gate v1",
        )
        self.blockers = [str(item) for item in self.blockers]
        self.warnings = [str(item) for item in self.warnings]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "source_prd_id": self.source_prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "missing_source_artifact_count": self.missing_source_artifact_count,
            "source_final_status": self.source_final_status,
            "source_decision": self.source_decision,
            "new_execution_performed": self.new_execution_performed,
            "provider_called_by_results_gate": self.provider_called_by_results_gate,
            "target_operator_count": self.target_operator_count,
            "scenario_count": self.scenario_count,
            "provider_calls_total": self.provider_calls_total,
            "provider_budget_gate_passed": self.provider_budget_gate_passed,
            "normal_user_controls_total": self.normal_user_controls_total,
            "normal_user_apply_count": self.normal_user_apply_count,
            "normal_user_provider_calls_total": self.normal_user_provider_calls_total,
            "normal_user_no_effect_passed": self.normal_user_no_effect_passed,
            "quality_micro_shift_gate_passed": self.quality_micro_shift_gate_passed,
            "candidate_weaker_than_baseline_count": self.candidate_weaker_than_baseline_count,
            "hard_fail_count": self.hard_fail_count,
            "response_quality_regression_count": self.response_quality_regression_count,
            "rollback_gate_passed": self.rollback_gate_passed,
            "rollback_failure_count": self.rollback_failure_count,
            "stale_apply_after_force_disabled_count": self.stale_apply_after_force_disabled_count,
            "hard_stop_triggered": self.hard_stop_triggered,
            "safety_kb_boundary_gate_passed": self.safety_kb_boundary_gate_passed,
            "raw_kb_text_exposure_count": self.raw_kb_text_exposure_count,
            "kb_authority_violation_count": self.kb_authority_violation_count,
            "unsafe_practice_suggestion_count": self.unsafe_practice_suggestion_count,
            "trace_provider_sanitization_gate_passed": self.trace_provider_sanitization_gate_passed,
            "raw_provider_payload_committed_count": self.raw_provider_payload_committed_count,
            "secret_like_value_count": self.secret_like_value_count,
            "private_log_leak_count": self.private_log_leak_count,
            "botdb_stability_gate_passed": self.botdb_stability_gate_passed,
            "botdb_query_ok": self.botdb_query_ok,
            "botdb_semantic_fallback_used": self.botdb_semantic_fallback_used,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "production_data_mutated": self.production_data_mutated,
            "kb_registry_chroma_config_mutated": self.kb_registry_chroma_config_mutated,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "utf8_decode_error_count": self.utf8_decode_error_count,
            "nul_byte_file_count": self.nul_byte_file_count,
            "json_parse_error_count": self.json_parse_error_count,
            "replacement_char_warning_count": self.replacement_char_warning_count,
            "docs_consistency_passed": self.docs_consistency_passed,
            "project_state_synced": self.project_state_synced,
            "roadmap_synced": self.roadmap_synced,
            "prd_index_synced": self.prd_index_synced,
            "decisions_synced": self.decisions_synced,
            "stale_next_prd_reference_count": self.stale_next_prd_reference_count,
            "duplicate_roadmap_next_item_count": self.duplicate_roadmap_next_item_count,
            "next_recommended_prd": self.next_recommended_prd,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


__all__ = ["ControlledRolloutResultsGateDecisionV1"]
