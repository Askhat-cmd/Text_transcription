"""Contracts for PRD-046.1.22 provider-backed smoke readiness planning."""

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


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ProviderBackedSmokeReadinessStatus:
    final_status: str = "failed"
    decision: str = "provider_backed_readiness_blocked"
    diagnostic_center_source_gate_passed: bool = False
    botdb_recovery_source_gate_passed: bool = False
    live_dependency_readiness_passed: bool = False
    cohort_policy_ready: bool = False
    toggle_matrix_ready: bool = False
    scenario_pack_ready: bool = False
    normal_user_control_plan_ready: bool = False
    rollback_first_runbook_ready: bool = False
    hard_stop_criteria_ready: bool = False
    kb_boundary_contract_ready: bool = False
    trace_sanitization_contract_ready: bool = False
    execution_manifest_template_ready: bool = False
    provider_execution_performed: bool = False
    provider_called: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    future_execution_requires_new_prd: bool = True
    no_mutation_proof_passed: bool = False
    artifact_encoding_hygiene_passed: bool = False
    docs_synced: bool = False

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "provider_backed_readiness_blocked")
        self.diagnostic_center_source_gate_passed = _as_bool(self.diagnostic_center_source_gate_passed, False)
        self.botdb_recovery_source_gate_passed = _as_bool(self.botdb_recovery_source_gate_passed, False)
        self.live_dependency_readiness_passed = _as_bool(self.live_dependency_readiness_passed, False)
        self.cohort_policy_ready = _as_bool(self.cohort_policy_ready, False)
        self.toggle_matrix_ready = _as_bool(self.toggle_matrix_ready, False)
        self.scenario_pack_ready = _as_bool(self.scenario_pack_ready, False)
        self.normal_user_control_plan_ready = _as_bool(self.normal_user_control_plan_ready, False)
        self.rollback_first_runbook_ready = _as_bool(self.rollback_first_runbook_ready, False)
        self.hard_stop_criteria_ready = _as_bool(self.hard_stop_criteria_ready, False)
        self.kb_boundary_contract_ready = _as_bool(self.kb_boundary_contract_ready, False)
        self.trace_sanitization_contract_ready = _as_bool(self.trace_sanitization_contract_ready, False)
        self.execution_manifest_template_ready = _as_bool(self.execution_manifest_template_ready, False)
        self.provider_execution_performed = _as_bool(self.provider_execution_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.future_execution_requires_new_prd = _as_bool(self.future_execution_requires_new_prd, True)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.artifact_encoding_hygiene_passed = _as_bool(self.artifact_encoding_hygiene_passed, False)
        self.docs_synced = _as_bool(self.docs_synced, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "diagnostic_center_source_gate_passed": self.diagnostic_center_source_gate_passed,
            "botdb_recovery_source_gate_passed": self.botdb_recovery_source_gate_passed,
            "live_dependency_readiness_passed": self.live_dependency_readiness_passed,
            "cohort_policy_ready": self.cohort_policy_ready,
            "toggle_matrix_ready": self.toggle_matrix_ready,
            "scenario_pack_ready": self.scenario_pack_ready,
            "normal_user_control_plan_ready": self.normal_user_control_plan_ready,
            "rollback_first_runbook_ready": self.rollback_first_runbook_ready,
            "hard_stop_criteria_ready": self.hard_stop_criteria_ready,
            "kb_boundary_contract_ready": self.kb_boundary_contract_ready,
            "trace_sanitization_contract_ready": self.trace_sanitization_contract_ready,
            "execution_manifest_template_ready": self.execution_manifest_template_ready,
            "provider_execution_performed": self.provider_execution_performed,
            "provider_called": self.provider_called,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "future_execution_requires_new_prd": self.future_execution_requires_new_prd,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "artifact_encoding_hygiene_passed": self.artifact_encoding_hygiene_passed,
            "docs_synced": self.docs_synced,
        }


@dataclass
class ProviderBackedSmokeReadinessDecision:
    schema_version: str = "diagnostic_center_provider_backed_smoke_readiness_decision_v1"
    prd_id: str = "PRD-046.1.22"
    final_status: str = "failed"
    decision: str = "provider_backed_readiness_blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_prd: str = "PRD-046.1.22-HF1 - Provider-backed readiness blocker hotfix"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_provider_backed_smoke_readiness_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.22")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "provider_backed_readiness_blocked")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.recommended_next_prd = _as_str(
            self.recommended_next_prd,
            "PRD-046.1.22-HF1 - Provider-backed readiness blocker hotfix",
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
class ProviderBackedSmokeReadinessBundle:
    source_gate: dict[str, Any] = field(default_factory=dict)
    botdb_recovery_gate: dict[str, Any] = field(default_factory=dict)
    live_dependency_gate: dict[str, Any] = field(default_factory=dict)
    provider_readiness_policy: dict[str, Any] = field(default_factory=dict)
    cohort_policy: dict[str, Any] = field(default_factory=dict)
    toggle_matrix: dict[str, Any] = field(default_factory=dict)
    scenario_pack: dict[str, Any] = field(default_factory=dict)
    normal_user_control_plan: dict[str, Any] = field(default_factory=dict)
    rollback_first_runbook: dict[str, Any] = field(default_factory=dict)
    hard_stop_criteria: dict[str, Any] = field(default_factory=dict)
    kb_boundary_contract: dict[str, Any] = field(default_factory=dict)
    trace_sanitization_contract: dict[str, Any] = field(default_factory=dict)
    provider_budget_contract: dict[str, Any] = field(default_factory=dict)
    execution_manifest_template: dict[str, Any] = field(default_factory=dict)
    readiness_scorecard: dict[str, Any] = field(default_factory=dict)
    next_prd_recommendation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.botdb_recovery_gate = _safe_dict(self.botdb_recovery_gate)
        self.live_dependency_gate = _safe_dict(self.live_dependency_gate)
        self.provider_readiness_policy = _safe_dict(self.provider_readiness_policy)
        self.cohort_policy = _safe_dict(self.cohort_policy)
        self.toggle_matrix = _safe_dict(self.toggle_matrix)
        self.scenario_pack = _safe_dict(self.scenario_pack)
        self.normal_user_control_plan = _safe_dict(self.normal_user_control_plan)
        self.rollback_first_runbook = _safe_dict(self.rollback_first_runbook)
        self.hard_stop_criteria = _safe_dict(self.hard_stop_criteria)
        self.kb_boundary_contract = _safe_dict(self.kb_boundary_contract)
        self.trace_sanitization_contract = _safe_dict(self.trace_sanitization_contract)
        self.provider_budget_contract = _safe_dict(self.provider_budget_contract)
        self.execution_manifest_template = _safe_dict(self.execution_manifest_template)
        self.readiness_scorecard = _safe_dict(self.readiness_scorecard)
        self.next_prd_recommendation = _safe_dict(self.next_prd_recommendation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "botdb_recovery_gate": dict(self.botdb_recovery_gate),
            "live_dependency_gate": dict(self.live_dependency_gate),
            "provider_readiness_policy": dict(self.provider_readiness_policy),
            "cohort_policy": dict(self.cohort_policy),
            "toggle_matrix": dict(self.toggle_matrix),
            "scenario_pack": dict(self.scenario_pack),
            "normal_user_control_plan": dict(self.normal_user_control_plan),
            "rollback_first_runbook": dict(self.rollback_first_runbook),
            "hard_stop_criteria": dict(self.hard_stop_criteria),
            "kb_boundary_contract": dict(self.kb_boundary_contract),
            "trace_sanitization_contract": dict(self.trace_sanitization_contract),
            "provider_budget_contract": dict(self.provider_budget_contract),
            "execution_manifest_template": dict(self.execution_manifest_template),
            "readiness_scorecard": dict(self.readiness_scorecard),
            "next_prd_recommendation": dict(self.next_prd_recommendation),
        }
