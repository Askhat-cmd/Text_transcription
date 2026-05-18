"""PRD-046.1.19 Diagnostic Center runtime pilot readiness planning (plan-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_runtime_pilot_readiness_v1 import (
    DiagnosticCenterPilotCohortPolicy,
    DiagnosticCenterRuntimePilotReadinessDecision,
    DiagnosticCenterRuntimePilotReadinessStatus,
)

PRD = "PRD-046.1.19"
SOURCE_PRD = "PRD-046.1.18"
NEXT_PRD_IF_PASSED = "PRD-046.1.20 - Diagnostic Center Controlled Runtime Pilot Execution / Limited Live Smoke v1"
NEXT_PRD_IF_BLOCKED = "PRD-046.1.19-HF1 - Runtime Pilot Readiness blocker hotfix"

REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.18_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.18_RESPONSE_QUALITY_CALIBRATION_REPORT.md",
    "PRD-046.1.18_WEAK_CASE_CLOSURE_REPORT.md",
    "PRD-046.1.18_NEXT_PRD_RECOMMENDATION.md",
)
REQUIRED_SOURCE_LOG_FILES = {
    "source_scorecard": "diagnostic_center_response_quality_calibration_scorecard.json",
    "source_no_runtime_gate": "no_runtime_authority_expansion_gate.json",
    "source_no_mutation": "no_mutation_proof.json",
    "source_artifact_hygiene": "artifact_encoding_hygiene_report.json",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def required_source_artifacts(source_dir: Path, reports_dir: Path) -> dict[str, Path]:
    required: dict[str, Path] = {}
    for report_name in REQUIRED_SOURCE_REPORT_FILES:
        required[f"report:{report_name}"] = reports_dir / report_name
    for key, file_name in REQUIRED_SOURCE_LOG_FILES.items():
        required[key] = source_dir / file_name
    return required


def preflight_source(source_dir: Path, reports_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_dir, reports_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            parsed[key] = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {k: str(v.resolve()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    scorecard = _safe_dict(parsed.get("source_scorecard"))
    no_runtime_gate = _safe_dict(parsed.get("source_no_runtime_gate"))
    no_mutation = _safe_dict(parsed.get("source_no_mutation"))
    hygiene = _safe_dict(parsed.get("source_artifact_hygiene"))

    final_status = str(scorecard.get("final_status", "failed"))
    decision = str(scorecard.get("decision", "blocked"))
    hard_fail_detection_rate = _as_float(scorecard.get("hard_fail_detection_rate"), 0.0)
    kb_boundary_detection_rate = _as_float(scorecard.get("kb_boundary_respect_hard_fail_detection_rate"), 0.0)
    weak_groups_closed = (
        _as_float(scorecard.get("state_depth_fit_weak_detection_rate"), 0.0) >= 0.90
        and _as_float(scorecard.get("non_directiveness_weak_detection_rate"), 0.0) >= 0.90
        and _as_float(scorecard.get("non_bookishness_weak_detection_rate"), 0.0) >= 0.90
        and kb_boundary_detection_rate >= 1.0
    )

    source_gate = {
        "source_prd": SOURCE_PRD,
        "source_final_status": final_status,
        "source_decision": decision,
        "weak_case_groups_closed": weak_groups_closed,
        "hard_fail_detection_rate": hard_fail_detection_rate,
        "kb_boundary_respect_hard_fail_detection_rate": kb_boundary_detection_rate,
        "provider_called": _as_bool(scorecard.get("provider_called"), True),
        "runtime_activation_performed": _as_bool(scorecard.get("runtime_activation_performed"), True),
        "production_mutation_detected": _as_bool(scorecard.get("production_mutation_detected"), True),
        "no_runtime_authority_expansion_passed": (
            _as_bool(scorecard.get("no_runtime_authority_expansion_passed"), False)
            and str(no_runtime_gate.get("final_status", "failed")) == "passed"
        ),
        "artifact_encoding_hygiene_passed": (
            _as_bool(scorecard.get("artifact_encoding_hygiene_passed"), False)
            and str(hygiene.get("final_status", "failed")) == "passed"
        ),
        "source_no_mutation_passed": (
            _as_bool(no_mutation.get("all_blocks_merged_mutated"), True) is False
            and _as_bool(no_mutation.get("registry_mutated"), True) is False
            and _as_bool(no_mutation.get("config_mutated"), True) is False
            and _as_bool(no_mutation.get("provider_called"), True) is False
        ),
        "reports_and_logs_present": preflight_ok,
    }
    source_gate["source_gate_passed"] = (
        source_gate["source_final_status"] == "passed"
        and source_gate["source_decision"] == "response_quality_calibration_passed"
        and source_gate["weak_case_groups_closed"] is True
        and source_gate["hard_fail_detection_rate"] >= 1.0
        and source_gate["kb_boundary_respect_hard_fail_detection_rate"] >= 1.0
        and source_gate["provider_called"] is False
        and source_gate["runtime_activation_performed"] is False
        and source_gate["production_mutation_detected"] is False
        and source_gate["no_runtime_authority_expansion_passed"] is True
        and source_gate["artifact_encoding_hygiene_passed"] is True
        and source_gate["source_no_mutation_passed"] is True
        and source_gate["reports_and_logs_present"] is True
    )
    return source_gate


def build_pilot_scope() -> dict[str, Any]:
    payload = {
        "schema_version": "runtime_pilot_scope_v1",
        "prd": PRD,
        "pilot_type": "limited_live_smoke_plan_only",
        "execution_performed": False,
        "provider_called": False,
        "runtime_activation_performed": False,
        "broad_rollout_allowed": False,
        "normal_user_apply_allowed": False,
        "future_execution_requires_new_prd": True,
    }
    payload["pilot_scope_ready"] = True
    payload["final_status"] = "passed"
    return payload


def build_cohort_policy() -> dict[str, Any]:
    payload = DiagnosticCenterPilotCohortPolicy().to_dict()
    payload.update(
        {
            "schema_version": "runtime_pilot_cohort_policy_v1",
            "prd": PRD,
            "ready": (
                payload["max_initial_cohort_size"] == 1
                and payload["normal_user_control_count"] >= 2
                and payload["normal_user_apply_allowed"] is False
                and payload["operator_user_required"] is True
            ),
            "final_status": "passed",
        }
    )
    return payload


def build_toggle_matrix() -> dict[str, Any]:
    matrix = {
        "PROMPT_CONSTRAINT_PILOT_ENABLED": {
            "default_state": "false",
            "planned_execution_state_for_future_prd": "true",
            "rollback_state": "false",
            "hard_stop_state": "false",
            "normal_user_state": "false",
        },
        "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": {
            "default_state": "true",
            "planned_execution_state_for_future_prd": "false",
            "rollback_state": "true",
            "hard_stop_state": "true",
            "normal_user_state": "true",
        },
        "PROMPT_CONSTRAINT_PILOT_MODE": {
            "default_state": "shadow",
            "planned_execution_state_for_future_prd": "test_apply",
            "rollback_state": "shadow",
            "hard_stop_state": "shadow",
            "normal_user_state": "shadow",
        },
        "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": {
            "default_state": "",
            "planned_execution_state_for_future_prd": "pilot_runtime_operator_001",
            "rollback_state": "",
            "hard_stop_state": "",
            "normal_user_state": "",
        },
        "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": {
            "default_state": "pilot_",
            "planned_execution_state_for_future_prd": "pilot_",
            "rollback_state": "pilot_",
            "hard_stop_state": "pilot_",
            "normal_user_state": "pilot_",
        },
        "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": {
            "default_state": "600",
            "planned_execution_state_for_future_prd": "600",
            "rollback_state": "600",
            "hard_stop_state": "600",
            "normal_user_state": "600",
        },
        "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": {
            "default_state": "0.30",
            "planned_execution_state_for_future_prd": "0.30",
            "rollback_state": "0.30",
            "hard_stop_state": "0.30",
            "normal_user_state": "0.30",
        },
    }
    ready = matrix["PROMPT_CONSTRAINT_PILOT_ENABLED"]["default_state"] == "false" and matrix["PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"]["default_state"] == "true"
    return {
        "schema_version": "runtime_pilot_toggle_matrix_v1",
        "prd": PRD,
        "matrix": matrix,
        "force_disabled_absolute_rollback_priority": True,
        "ready": ready,
        "final_status": "passed" if ready else "failed",
    }


def build_runtime_preflight_requirements() -> dict[str, Any]:
    requirements = [
        "Git working tree clean before execution.",
        "PROJECT_STATE/ROADMAP/PRD_INDEX synced.",
        "PRD-046.1.18 scorecard passed.",
        "Feature flag defaults conservative.",
        "BotDB admin API reachable when live smoke requires it.",
        "Chroma focus source consistency confirmed: source=123__кузница_духа, registry=247, chroma=247.",
        "KB/internal lens boundary gate passed.",
        "Trace sanitization gate ready.",
        "Normal-user control scenarios prepared.",
        "Rollback-first runbook ready.",
    ]
    return {
        "schema_version": "runtime_pilot_preflight_requirements_v1",
        "prd": PRD,
        "requirements": requirements,
        "botdb_launch_reference": [
            "cd C:\\My_practice\\Text_transcription\\Bot_data_base",
            ".venv\\Scripts\\Activate.ps1",
            "python -m uvicorn api.main:app --reload --port 8003",
        ],
        "ready": len(requirements) >= 10,
        "final_status": "passed",
    }


def build_limited_live_smoke_plan() -> dict[str, Any]:
    return {
        "schema_version": "limited_live_smoke_plan_v1",
        "prd": PRD,
        "execution_performed": False,
        "scenarios": [
            {"id": "low_resource_support", "expected": "short_stabilizing_non_overanalytical_response"},
            {"id": "self_blame_pattern", "expected": "separate_person_from_pattern_without_shame"},
            {"id": "directive_request", "expected": "return_agency_without_directive_life_command"},
            {"id": "anger_externalization", "expected": "validate_feeling_without_world_blame_alliance"},
            {"id": "kb_lens_boundary", "expected": "no_raw_quote_no_authority_citation_no_bookish_lecture"},
            {"id": "normal_user_control", "expected": "no_apply_no_prompt_or_contract_or_final_answer_change"},
        ],
        "expected_artifacts_for_execution_prd": [
            "live_smoke_manifest.json",
            "pilot_user_trace_samples_sanitized.json",
            "normal_user_control_trace_samples_sanitized.json",
            "baseline_vs_pilot_quality_delta.json",
            "rollback_proof.json",
            "hard_stop_evaluation.json",
            "monitoring_scorecard.json",
            "no_mutation_proof.json",
            "artifact_encoding_hygiene_report.json",
        ],
        "ready": True,
        "final_status": "passed",
    }


def build_rollback_first_runbook() -> dict[str, Any]:
    return {
        "schema_version": "runtime_pilot_rollback_first_runbook_v1",
        "prd": PRD,
        "before_execution": [
            "verify_force_disabled_default_true",
            "capture_pre_execution_hashes",
            "prepare_operator_allowlist_only",
        ],
        "during_execution": [
            "monitor_normal_user_apply_count",
            "monitor_boundary_and_safety_regressions",
            "capture_sanitized_traces_only",
        ],
        "if_any_hard_stop": [
            "set_PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true",
            "set_PROMPT_CONSTRAINT_PILOT_ENABLED=false",
            "set_PROMPT_CONSTRAINT_PILOT_MODE=shadow",
            "clear_PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS",
        ],
        "after_execution": [
            "test_rollback_on_allowlisted_user",
            "test_rollback_on_normal_user_control",
            "confirm_stale_apply_after_force_disabled_count=0",
        ],
        "post_push_report_sync": [
            "update_implementation_report_commit_hash",
            "update_push_status",
            "verify_docs_sync",
        ],
        "rollback_must_be_tested_before_pilot_apply": True,
        "rollback_must_be_tested_after_pilot_apply": True,
        "stale_apply_after_force_disabled_is_blocker": True,
        "normal_user_apply_after_rollback_is_blocker": True,
        "ready": True,
        "final_status": "passed",
    }


def build_hard_stop_criteria() -> dict[str, Any]:
    criteria = [
        "normal_user_apply_count > 0",
        "writer_prompt_changed_for_normal_user=true",
        "writer_contract_changed_for_normal_user=true",
        "final_answer_changed_for_normal_user=true",
        "raw_kb_quote_exposure_count > 0",
        "kuznitsa_authority_citation_count > 0",
        "high_stakes_directive_advice_detected=true",
        "safety_regression_count > 0",
        "kb_boundary_violation_count > 0",
        "trace_sanitization_violation_count > 0",
        "rollback_failure_count > 0",
        "stale_apply_after_force_disabled_count > 0",
        "provider_error_leaks_into_user_facing_output=true",
        "production_mutation_detected=true",
    ]
    return {
        "schema_version": "runtime_pilot_hard_stop_criteria_v1",
        "prd": PRD,
        "hard_stop_if": criteria,
        "ready": len(criteria) >= 10,
        "final_status": "passed",
    }


def build_monitoring_artifact_contract() -> dict[str, Any]:
    required = [
        "sanitized_trace_samples",
        "baseline_vs_pilot_comparison",
        "response_quality_dimensions",
        "prompt_delta_size",
        "safety_and_kb_boundary_results",
        "normal_user_no_effect_proof",
        "rollback_proof",
        "no_mutation_proof",
        "artifact_encoding_hygiene_report",
        "final_decision",
    ]
    return {
        "schema_version": "runtime_pilot_monitoring_artifact_contract_v1",
        "prd": PRD,
        "required_artifacts": required,
        "raw_private_logs_allowed": False,
        "ready": len(required) >= 10,
        "final_status": "passed",
    }


def build_normal_user_guard() -> dict[str, Any]:
    return {
        "schema_version": "runtime_pilot_normal_user_guard_v1",
        "prd": PRD,
        "normal_user_apply_allowed": False,
        "normal_user_control_required": True,
        "normal_user_control_count": 2,
        "normal_user_prompt_change_allowed": False,
        "normal_user_contract_change_allowed": False,
        "normal_user_final_answer_change_allowed": False,
        "final_status": "passed",
    }


def build_kb_governance_guard() -> dict[str, Any]:
    return {
        "schema_version": "runtime_pilot_kb_governance_guard_v1",
        "prd": PRD,
        "chunk_type_authority": "deterministic",
        "allowed_use_authority": "deterministic",
        "safety_flags_authority": "deterministic",
        "llm_enrichment_role": "advisory",
        "kuznitsa_duha_role": "internal_lens_library",
        "raw_quote_allowed": False,
        "authority_citation_allowed": False,
        "internal_only_direct_use_allowed": False,
        "not_for_direct_quote_respected": True,
        "final_status": "passed",
    }


def build_trace_sanitization_guard() -> dict[str, Any]:
    return {
        "schema_version": "runtime_pilot_trace_sanitization_guard_v1",
        "prd": PRD,
        "raw_private_logs_allowed": False,
        "raw_content_full_allowed": False,
        "secret_like_values_allowed": False,
        "env_values_allowed": False,
        "sanitized_trace_required": True,
        "artifact_encoding_hygiene_required": True,
        "final_status": "passed",
    }


def build_docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions = (repo_root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    has_project = "PRD-046.1.19" in project_state
    has_roadmap = "PRD-046.1.19" in roadmap and "PRD-046.1.20" in roadmap
    has_index = "PRD-046.1.19" in prd_index
    has_readiness_policy = "Controlled runtime pilot requires readiness plan" in decisions
    docs_synced = has_project and has_roadmap and has_index
    return {
        "project_state_synced": has_project,
        "roadmap_synced": has_roadmap,
        "prd_index_synced": has_index,
        "readiness_policy_adr_present": has_readiness_policy,
        "docs_synced": docs_synced,
    }


def decide_final_status(
    *,
    source_gate: dict[str, Any],
    pilot_scope: dict[str, Any],
    cohort_policy: dict[str, Any],
    toggle_matrix: dict[str, Any],
    runtime_preflight_requirements: dict[str, Any],
    limited_live_smoke_plan: dict[str, Any],
    rollback_first_runbook: dict[str, Any],
    hard_stop_criteria: dict[str, Any],
    monitoring_artifact_contract: dict[str, Any],
    normal_user_guard: dict[str, Any],
    kb_governance_guard: dict[str, Any],
    trace_sanitization_guard: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene_passed: bool,
    docs_sync: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    no_mutation_ok = (
        _as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("registry_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("config_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("chroma_reindex_performed"), True) is False
        and _as_bool(no_mutation_proof.get("runtime_defaults_changed"), True) is False
        and _as_bool(no_mutation_proof.get("writer_prompt_runtime_changed"), True) is False
        and _as_bool(no_mutation_proof.get("writer_contract_runtime_changed"), True) is False
        and _as_bool(no_mutation_proof.get("normal_user_path_changed"), True) is False
        and _as_bool(no_mutation_proof.get("provider_called"), True) is False
    )

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if pilot_scope.get("final_status") != "passed":
        blockers.append("pilot_scope_not_ready")
    if cohort_policy.get("final_status") != "passed" or not _as_bool(cohort_policy.get("ready"), False):
        blockers.append("cohort_policy_not_ready")
    if toggle_matrix.get("final_status") != "passed" or not _as_bool(toggle_matrix.get("ready"), False):
        blockers.append("toggle_matrix_not_ready")
    if runtime_preflight_requirements.get("final_status") != "passed":
        blockers.append("runtime_preflight_requirements_not_ready")
    if limited_live_smoke_plan.get("final_status") != "passed":
        blockers.append("limited_live_smoke_plan_not_ready")
    if rollback_first_runbook.get("final_status") != "passed":
        blockers.append("rollback_first_runbook_not_ready")
    if hard_stop_criteria.get("final_status") != "passed":
        blockers.append("hard_stop_criteria_not_ready")
    if monitoring_artifact_contract.get("final_status") != "passed":
        blockers.append("monitoring_artifact_contract_not_ready")
    if normal_user_guard.get("final_status") != "passed":
        blockers.append("normal_user_guard_failed")
    if kb_governance_guard.get("final_status") != "passed":
        blockers.append("kb_governance_guard_failed")
    if trace_sanitization_guard.get("final_status") != "passed":
        blockers.append("trace_sanitization_guard_failed")
    if not no_mutation_ok:
        blockers.append("mutation_detected")
    if not artifact_hygiene_passed:
        blockers.append("artifact_hygiene_failed")
    if not _as_bool(docs_sync.get("docs_synced"), False):
        blockers.append("docs_not_synced")

    if blockers:
        final_status = "failed"
        decision = "blocked_runtime_pilot_readiness"
        recommended_next_prd = NEXT_PRD_IF_BLOCKED
    else:
        final_status = "passed"
        decision = "runtime_pilot_readiness_plan_ready"
        recommended_next_prd = NEXT_PRD_IF_PASSED

    status = DiagnosticCenterRuntimePilotReadinessStatus(
        final_status=final_status,
        decision=decision,
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        pilot_scope_ready=pilot_scope.get("final_status") == "passed",
        cohort_policy_ready=cohort_policy.get("final_status") == "passed",
        toggle_matrix_ready=toggle_matrix.get("final_status") == "passed",
        runtime_preflight_requirements_ready=runtime_preflight_requirements.get("final_status") == "passed",
        limited_live_smoke_plan_ready=limited_live_smoke_plan.get("final_status") == "passed",
        rollback_first_runbook_ready=rollback_first_runbook.get("final_status") == "passed",
        hard_stop_criteria_ready=hard_stop_criteria.get("final_status") == "passed",
        monitoring_artifact_contract_ready=monitoring_artifact_contract.get("final_status") == "passed",
        normal_user_guard_passed=normal_user_guard.get("final_status") == "passed",
        kb_governance_guard_passed=kb_governance_guard.get("final_status") == "passed",
        trace_sanitization_guard_passed=trace_sanitization_guard.get("final_status") == "passed",
        execution_performed=False,
        runtime_activation_performed=False,
        provider_called=False,
        broad_rollout_allowed=False,
        normal_user_apply_allowed=False,
        future_execution_requires_new_prd=True,
    ).to_dict()

    status.update(
        {
            "production_mutation_detected": not no_mutation_ok,
            "all_blocks_merged_mutated": _as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), False),
            "registry_mutated": _as_bool(no_mutation_proof.get("registry_mutated"), False),
            "config_mutated": _as_bool(no_mutation_proof.get("config_mutated"), False),
            "chroma_reindex_performed": _as_bool(no_mutation_proof.get("chroma_reindex_performed"), False),
            "runtime_defaults_changed": _as_bool(no_mutation_proof.get("runtime_defaults_changed"), False),
            "artifact_encoding_hygiene_passed": artifact_hygiene_passed,
            "docs_synced": _as_bool(docs_sync.get("docs_synced"), False),
            "recommended_next_prd": recommended_next_prd,
            "blockers": blockers,
            "warnings": warnings,
        }
    )

    decision_payload = DiagnosticCenterRuntimePilotReadinessDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()
    return status, decision_payload
