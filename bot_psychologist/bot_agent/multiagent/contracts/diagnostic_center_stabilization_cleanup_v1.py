"""Contracts for PRD-046.1.29 stabilization cleanup gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALLOWED_ZONES = {
    "production_runtime",
    "permanent_quality_eval_regression",
    "historical_archive",
    "cleanup_candidate_manifest_only",
    "do_not_touch",
    "unknown_requires_review",
}



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



def _as_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)



def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []



def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class CleanupZone:
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        normalized = _as_str(self.name, "unknown_requires_review")
        self.name = normalized if normalized in ALLOWED_ZONES else "unknown_requires_review"
        self.description = _as_str(self.description, "")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}


@dataclass
class CleanupSourceGateResult:
    schema_version: str = "diagnostic_center_stabilization_cleanup_source_gate_v1"
    prd: str = "PRD-046.1.29"
    source_prd: str = "PRD-046.1.28"
    source_gate_passed: bool = False
    final_status: str = "blocked"
    decision: str = "blocked"
    provider_scenarios_total: int = 0
    normal_user_apply_count_total: int = 0
    normal_user_provider_calls_total: int = 0
    rollback_failure_count_total: int = 0
    safety_kb_boundary_gate_passed: bool = False
    trace_provider_sanitization_gate_passed: bool = False
    botdb_stability_gate_passed: bool = False
    no_mutation_proof_passed: bool = False
    blockers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_stabilization_cleanup_source_gate_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.source_prd = _as_str(self.source_prd, "PRD-046.1.28")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked")
        self.provider_scenarios_total = _as_int(self.provider_scenarios_total, 0)
        self.normal_user_apply_count_total = _as_int(self.normal_user_apply_count_total, 0)
        self.normal_user_provider_calls_total = _as_int(self.normal_user_provider_calls_total, 0)
        self.rollback_failure_count_total = _as_int(self.rollback_failure_count_total, 0)
        self.safety_kb_boundary_gate_passed = _as_bool(self.safety_kb_boundary_gate_passed, False)
        self.trace_provider_sanitization_gate_passed = _as_bool(self.trace_provider_sanitization_gate_passed, False)
        self.botdb_stability_gate_passed = _as_bool(self.botdb_stability_gate_passed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.blockers = [str(item) for item in _as_list(self.blockers)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_prd": self.source_prd,
            "source_gate_passed": self.source_gate_passed,
            "final_status": self.final_status,
            "decision": self.decision,
            "provider_scenarios_total": self.provider_scenarios_total,
            "normal_user_apply_count_total": self.normal_user_apply_count_total,
            "normal_user_provider_calls_total": self.normal_user_provider_calls_total,
            "rollback_failure_count_total": self.rollback_failure_count_total,
            "safety_kb_boundary_gate_passed": self.safety_kb_boundary_gate_passed,
            "trace_provider_sanitization_gate_passed": self.trace_provider_sanitization_gate_passed,
            "botdb_stability_gate_passed": self.botdb_stability_gate_passed,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "blockers": list(self.blockers),
        }


@dataclass
class DiagnosticCenterArtifactInventory:
    schema_version: str = "diagnostic_center_artifact_inventory_v1"
    prd: str = "PRD-046.1.29"
    items: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_artifact_inventory_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.items = [dict(item) for item in _as_list(self.items) if isinstance(item, dict)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "item_count": len(self.items),
            "items": list(self.items),
        }


@dataclass
class DiagnosticCenterArtifactClassification:
    schema_version: str = "diagnostic_center_artifact_classification_v1"
    prd: str = "PRD-046.1.29"
    zone_counts: dict[str, int] = field(default_factory=dict)
    required_zones_present: bool = False
    unknown_requires_review_count: int = 0

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_artifact_classification_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.zone_counts = {str(k): _as_int(v, 0) for k, v in _as_dict(self.zone_counts).items()}
        self.required_zones_present = _as_bool(self.required_zones_present, False)
        self.unknown_requires_review_count = _as_int(self.unknown_requires_review_count, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "zone_counts": dict(self.zone_counts),
            "required_zones_present": self.required_zones_present,
            "unknown_requires_review_count": self.unknown_requires_review_count,
        }


@dataclass
class ArchiveManifestEntry:
    path: str = ""
    zone: str = "historical_archive"
    reason: str = ""
    archive_target: str = ""
    delete_now: bool = False

    def __post_init__(self) -> None:
        self.path = _as_str(self.path, "")
        self.zone = _as_str(self.zone, "historical_archive")
        if self.zone not in ALLOWED_ZONES:
            self.zone = "unknown_requires_review"
        self.reason = _as_str(self.reason, "")
        self.archive_target = _as_str(self.archive_target, "")
        self.delete_now = _as_bool(self.delete_now, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "zone": self.zone,
            "reason": self.reason,
            "archive_target": self.archive_target,
            "delete_now": self.delete_now,
        }


@dataclass
class CleanupCandidateEntry:
    path: str = ""
    reason: str = ""
    requires_manual_approval: bool = True
    delete_now: bool = False

    def __post_init__(self) -> None:
        self.path = _as_str(self.path, "")
        self.reason = _as_str(self.reason, "")
        self.requires_manual_approval = _as_bool(self.requires_manual_approval, True)
        self.delete_now = _as_bool(self.delete_now, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "reason": self.reason,
            "requires_manual_approval": self.requires_manual_approval,
            "delete_now": self.delete_now,
        }


@dataclass
class DocsCompactionPlan:
    schema_version: str = "diagnostic_center_docs_compaction_plan_v1"
    prd: str = "PRD-046.1.29"
    snapshot_required: bool = True
    target_docs: list[str] = field(default_factory=list)
    compacted_docs: list[str] = field(default_factory=list)
    snapshot_dir: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_docs_compaction_plan_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.snapshot_required = _as_bool(self.snapshot_required, True)
        self.target_docs = [str(item) for item in _as_list(self.target_docs)]
        self.compacted_docs = [str(item) for item in _as_list(self.compacted_docs)]
        self.snapshot_dir = _as_str(self.snapshot_dir, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "snapshot_required": self.snapshot_required,
            "target_docs": list(self.target_docs),
            "compacted_docs": list(self.compacted_docs),
            "snapshot_dir": self.snapshot_dir,
        }


@dataclass
class DocsSnapshotProof:
    schema_version: str = "diagnostic_center_docs_snapshot_proof_v1"
    prd: str = "PRD-046.1.29"
    snapshot_dir: str = ""
    manifest_path: str = ""
    created: bool = False
    files: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_docs_snapshot_proof_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.snapshot_dir = _as_str(self.snapshot_dir, "")
        self.manifest_path = _as_str(self.manifest_path, "")
        self.created = _as_bool(self.created, False)
        self.files = [dict(item) for item in _as_list(self.files) if isinstance(item, dict)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "snapshot_dir": self.snapshot_dir,
            "manifest_path": self.manifest_path,
            "created": self.created,
            "files": list(self.files),
        }


@dataclass
class PermanentGateRevalidationResult:
    schema_version: str = "diagnostic_center_permanent_gate_revalidation_v1"
    prd: str = "PRD-046.1.29"
    gate_checks: dict[str, bool] = field(default_factory=dict)
    permanent_gate_revalidation_passed: bool = False
    missing_gates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_permanent_gate_revalidation_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.gate_checks = {str(k): _as_bool(v, False) for k, v in _as_dict(self.gate_checks).items()}
        self.permanent_gate_revalidation_passed = _as_bool(self.permanent_gate_revalidation_passed, False)
        self.missing_gates = [str(item) for item in _as_list(self.missing_gates)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "gate_checks": dict(self.gate_checks),
            "permanent_gate_revalidation_passed": self.permanent_gate_revalidation_passed,
            "missing_gates": list(self.missing_gates),
        }


@dataclass
class ArtifactHygieneNormalizationResult:
    schema_version: str = "diagnostic_center_artifact_hygiene_normalization_v1"
    prd: str = "PRD-046.1.29"
    utf8_decode_error_count: int = 0
    nul_byte_file_count: int = 0
    json_parse_error_count: int = 0
    current_generated_artifact_replacement_char_count: int = 0
    historical_warning_count: int = 0
    historical_warning_documented: bool = False
    artifact_hygiene_normalization_passed: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_artifact_hygiene_normalization_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.utf8_decode_error_count = _as_int(self.utf8_decode_error_count, 0)
        self.nul_byte_file_count = _as_int(self.nul_byte_file_count, 0)
        self.json_parse_error_count = _as_int(self.json_parse_error_count, 0)
        self.current_generated_artifact_replacement_char_count = _as_int(self.current_generated_artifact_replacement_char_count, 0)
        self.historical_warning_count = _as_int(self.historical_warning_count, 0)
        self.historical_warning_documented = _as_bool(self.historical_warning_documented, False)
        self.artifact_hygiene_normalization_passed = _as_bool(self.artifact_hygiene_normalization_passed, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "utf8_decode_error_count": self.utf8_decode_error_count,
            "nul_byte_file_count": self.nul_byte_file_count,
            "json_parse_error_count": self.json_parse_error_count,
            "current_generated_artifact_replacement_char_count": self.current_generated_artifact_replacement_char_count,
            "historical_warning_count": self.historical_warning_count,
            "historical_warning_documented": self.historical_warning_documented,
            "artifact_hygiene_normalization_passed": self.artifact_hygiene_normalization_passed,
        }


@dataclass
class StabilizationCleanupDecision:
    schema_version: str = "diagnostic_center_stabilization_cleanup_decision_v1"
    prd: str = "PRD-046.1.29"
    final_status: str = "blocked"
    decision: str = "blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_stabilization_cleanup_decision_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


@dataclass
class StabilizationCleanupScorecard:
    schema_version: str = "diagnostic_center_stabilization_cleanup_scorecard_v1"
    prd: str = "PRD-046.1.29"
    source_gate_passed: bool = False
    artifact_inventory_created: bool = False
    artifact_classification_created: bool = False
    archive_manifest_created: bool = False
    cleanup_candidate_manifest_created: bool = False
    docs_snapshots_created: bool = False
    docs_compaction_passed: bool = False
    runtime_map_created: bool = False
    eval_harness_map_created: bool = False
    permanent_gate_revalidation_passed: bool = False
    artifact_hygiene_normalization_passed: bool = False
    no_mutation_proof_passed: bool = False
    physical_runtime_file_deletion_count: int = 0
    safety_eval_gate_deletion_count: int = 0
    production_data_mutated: bool = False
    runtime_defaults_changed: bool = False
    provider_called: bool = False
    new_provider_execution_performed: bool = False
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    final_status: str = "blocked"
    decision: str = "blocked"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_stabilization_cleanup_scorecard_v1")
        self.prd = _as_str(self.prd, "PRD-046.1.29")
        self.source_gate_passed = _as_bool(self.source_gate_passed, False)
        self.artifact_inventory_created = _as_bool(self.artifact_inventory_created, False)
        self.artifact_classification_created = _as_bool(self.artifact_classification_created, False)
        self.archive_manifest_created = _as_bool(self.archive_manifest_created, False)
        self.cleanup_candidate_manifest_created = _as_bool(self.cleanup_candidate_manifest_created, False)
        self.docs_snapshots_created = _as_bool(self.docs_snapshots_created, False)
        self.docs_compaction_passed = _as_bool(self.docs_compaction_passed, False)
        self.runtime_map_created = _as_bool(self.runtime_map_created, False)
        self.eval_harness_map_created = _as_bool(self.eval_harness_map_created, False)
        self.permanent_gate_revalidation_passed = _as_bool(self.permanent_gate_revalidation_passed, False)
        self.artifact_hygiene_normalization_passed = _as_bool(self.artifact_hygiene_normalization_passed, False)
        self.no_mutation_proof_passed = _as_bool(self.no_mutation_proof_passed, False)
        self.physical_runtime_file_deletion_count = _as_int(self.physical_runtime_file_deletion_count, 0)
        self.safety_eval_gate_deletion_count = _as_int(self.safety_eval_gate_deletion_count, 0)
        self.production_data_mutated = _as_bool(self.production_data_mutated, False)
        self.runtime_defaults_changed = _as_bool(self.runtime_defaults_changed, False)
        self.provider_called = _as_bool(self.provider_called, False)
        self.new_provider_execution_performed = _as_bool(self.new_provider_execution_performed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd": self.prd,
            "source_gate_passed": self.source_gate_passed,
            "artifact_inventory_created": self.artifact_inventory_created,
            "artifact_classification_created": self.artifact_classification_created,
            "archive_manifest_created": self.archive_manifest_created,
            "cleanup_candidate_manifest_created": self.cleanup_candidate_manifest_created,
            "docs_snapshots_created": self.docs_snapshots_created,
            "docs_compaction_passed": self.docs_compaction_passed,
            "runtime_map_created": self.runtime_map_created,
            "eval_harness_map_created": self.eval_harness_map_created,
            "permanent_gate_revalidation_passed": self.permanent_gate_revalidation_passed,
            "artifact_hygiene_normalization_passed": self.artifact_hygiene_normalization_passed,
            "no_mutation_proof_passed": self.no_mutation_proof_passed,
            "physical_runtime_file_deletion_count": self.physical_runtime_file_deletion_count,
            "safety_eval_gate_deletion_count": self.safety_eval_gate_deletion_count,
            "production_data_mutated": self.production_data_mutated,
            "runtime_defaults_changed": self.runtime_defaults_changed,
            "provider_called": self.provider_called,
            "new_provider_execution_performed": self.new_provider_execution_performed,
            "broad_rollout_allowed": self.broad_rollout_allowed,
            "production_ready": self.production_ready,
            "normal_user_activation_allowed": self.normal_user_activation_allowed,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


__all__ = [
    "CleanupSourceGateResult",
    "DiagnosticCenterArtifactInventory",
    "DiagnosticCenterArtifactClassification",
    "CleanupZone",
    "ArchiveManifestEntry",
    "CleanupCandidateEntry",
    "DocsCompactionPlan",
    "DocsSnapshotProof",
    "PermanentGateRevalidationResult",
    "ArtifactHygieneNormalizationResult",
    "StabilizationCleanupDecision",
    "StabilizationCleanupScorecard",
    "ALLOWED_ZONES",
]
