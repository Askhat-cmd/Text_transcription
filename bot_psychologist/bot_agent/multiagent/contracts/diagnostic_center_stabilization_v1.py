"""Contracts for PRD-046.1.15 stabilization / cleanup / eval harness consolidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class DiagnosticCenterModuleInventoryItemV1:
    path: str = ""
    classification: str = "eval_harness"
    reason: str = ""
    runtime_critical: bool = False

    def __post_init__(self) -> None:
        self.path = _as_str(self.path, "")
        self.classification = _as_str(self.classification, "eval_harness")
        self.reason = _as_str(self.reason, "")
        self.runtime_critical = _as_bool(self.runtime_critical, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "classification": self.classification,
            "reason": self.reason,
            "runtime_critical": bool(self.runtime_critical),
        }


@dataclass
class DiagnosticCenterModuleClassificationV1:
    schema_version: str = "diagnostic_center_module_classification_v1"
    prd: str = "PRD-046.1.15"
    category_counts: dict[str, int] = field(default_factory=dict)
    required_categories_present: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_module_classification_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.15")
        self.category_counts = {str(k): _as_int(v, 0, minimum=0) for k, v in _safe_dict(self.category_counts).items()}
        self.required_categories_present = _as_bool(self.required_categories_present, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "category_counts": dict(self.category_counts),
            "required_categories_present": bool(self.required_categories_present),
        }


@dataclass
class DiagnosticCenterRegressionGateV1:
    gate_id: str = ""
    category: str = "runtime_safety"
    required: bool = True
    command_or_test: str = ""
    source_prds: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.gate_id = _as_str(self.gate_id, "")
        self.category = _as_str(self.category, "runtime_safety")
        self.required = _as_bool(self.required, True)
        self.command_or_test = _as_str(self.command_or_test, "")
        self.source_prds = [str(item) for item in _as_list(self.source_prds)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "category": self.category,
            "required": bool(self.required),
            "command_or_test": self.command_or_test,
            "source_prds": list(self.source_prds),
        }


@dataclass
class DiagnosticCenterArchiveCandidateV1:
    path: str = ""
    classification: str = "archive_candidate"
    reason: str = ""
    safe_to_archive_later: bool = True
    moved_now: bool = False
    delete_now: bool = False
    rollback_path: str | None = None

    def __post_init__(self) -> None:
        self.path = _as_str(self.path, "")
        self.classification = _as_str(self.classification, "archive_candidate")
        self.reason = _as_str(self.reason, "")
        self.safe_to_archive_later = _as_bool(self.safe_to_archive_later, True)
        self.moved_now = _as_bool(self.moved_now, False)
        self.delete_now = _as_bool(self.delete_now, False)
        self.rollback_path = None if self.rollback_path is None else _as_str(self.rollback_path, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "classification": self.classification,
            "reason": self.reason,
            "safe_to_archive_later": bool(self.safe_to_archive_later),
            "moved_now": bool(self.moved_now),
            "delete_now": bool(self.delete_now),
            "rollback_path": self.rollback_path,
        }


@dataclass
class DiagnosticCenterCleanupPlanV1:
    cleanup_mode: str = "non_destructive_manifest_first"
    physical_deletion_performed: bool = False
    runtime_files_deleted: bool = False
    regression_gates_deleted: bool = False
    kb_registry_chroma_config_mutated: bool = False
    archive_candidates_count: int = 0
    requires_future_cleanup_prd: bool = True
    future_cleanup_prd_recommended: str = "PRD-046.1.16 or later"

    def __post_init__(self) -> None:
        self.cleanup_mode = _as_str(self.cleanup_mode, "non_destructive_manifest_first")
        self.physical_deletion_performed = _as_bool(self.physical_deletion_performed, False)
        self.runtime_files_deleted = _as_bool(self.runtime_files_deleted, False)
        self.regression_gates_deleted = _as_bool(self.regression_gates_deleted, False)
        self.kb_registry_chroma_config_mutated = _as_bool(self.kb_registry_chroma_config_mutated, False)
        self.archive_candidates_count = _as_int(self.archive_candidates_count, 0, minimum=0)
        self.requires_future_cleanup_prd = _as_bool(self.requires_future_cleanup_prd, True)
        self.future_cleanup_prd_recommended = _as_str(self.future_cleanup_prd_recommended, "PRD-046.1.16 or later")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cleanup_mode": self.cleanup_mode,
            "physical_deletion_performed": bool(self.physical_deletion_performed),
            "runtime_files_deleted": bool(self.runtime_files_deleted),
            "regression_gates_deleted": bool(self.regression_gates_deleted),
            "kb_registry_chroma_config_mutated": bool(self.kb_registry_chroma_config_mutated),
            "archive_candidates_count": int(self.archive_candidates_count),
            "requires_future_cleanup_prd": bool(self.requires_future_cleanup_prd),
            "future_cleanup_prd_recommended": self.future_cleanup_prd_recommended,
        }


@dataclass
class DiagnosticCenterTransferBriefV1:
    path: str = ""
    ready: bool = False
    required_sections_present: bool = False

    def __post_init__(self) -> None:
        self.path = _as_str(self.path, "")
        self.ready = _as_bool(self.ready, False)
        self.required_sections_present = _as_bool(self.required_sections_present, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "ready": bool(self.ready),
            "required_sections_present": bool(self.required_sections_present),
        }


@dataclass
class DiagnosticCenterStabilizationDecisionV1:
    schema_version: str = "diagnostic_center_stabilization_decision_v1"
    prd: str = "PRD-046.1.15"
    final_status: str = "blocked"
    decision: str = "blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_step: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_stabilization_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.15")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.recommended_next_step = _as_str(self.recommended_next_step, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "recommended_next_step": self.recommended_next_step,
        }


@dataclass
class DiagnosticCenterStabilizationRunV1:
    schema_version: str = "diagnostic_center_stabilization_v1"
    prd: str = "PRD-046.1.15"
    source_prd: str = "PRD-046.1.14"
    source_decision: str = "ready_for_stabilization_cleanup"
    mode: str = "stabilization_cleanup_consolidation"
    new_execution_performed: bool = False
    provider_called: bool = False
    runtime_defaults_changed: bool = False
    module_inventory: dict[str, Any] = field(default_factory=dict)
    classification_summary: dict[str, Any] = field(default_factory=dict)
    regression_gate_catalog: dict[str, Any] = field(default_factory=dict)
    cleanup_plan: dict[str, Any] = field(default_factory=dict)
    archive_manifest: dict[str, Any] = field(default_factory=dict)
    transfer_brief: dict[str, Any] = field(default_factory=dict)
    decision: str = "blocked"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_stabilization_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.15")
        self.source_prd = _as_str(self.source_prd, "PRD-046.1.14")
        self.source_decision = _as_str(self.source_decision, "ready_for_stabilization_cleanup")
        self.mode = _as_str(self.mode, "stabilization_cleanup_consolidation")
        self.new_execution_performed = _as_bool(self.new_execution_performed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.module_inventory = _safe_dict(self.module_inventory)
        self.classification_summary = _safe_dict(self.classification_summary)
        self.regression_gate_catalog = _safe_dict(self.regression_gate_catalog)
        self.cleanup_plan = _safe_dict(self.cleanup_plan)
        self.archive_manifest = _safe_dict(self.archive_manifest)
        self.transfer_brief = _safe_dict(self.transfer_brief)
        self.decision = _as_str(self.decision, "blocked")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_prd": self.source_prd,
            "source_decision": self.source_decision,
            "mode": self.mode,
            "new_execution_performed": bool(self.new_execution_performed),
            "provider_called": bool(self.provider_called),
            "runtime_defaults_changed": bool(self.runtime_defaults_changed),
            "module_inventory": dict(self.module_inventory),
            "classification_summary": dict(self.classification_summary),
            "regression_gate_catalog": dict(self.regression_gate_catalog),
            "cleanup_plan": dict(self.cleanup_plan),
            "archive_manifest": dict(self.archive_manifest),
            "transfer_brief": dict(self.transfer_brief),
            "decision": self.decision,
        }
