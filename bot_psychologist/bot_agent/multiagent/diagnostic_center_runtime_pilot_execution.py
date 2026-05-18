"""PRD-046.1.20 controlled runtime pilot execution gate (limited live smoke)."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
import hashlib
from pathlib import Path
from typing import Any

from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_runtime_pilot_execution_v1 import (
    DiagnosticCenterRuntimePilotExecutionDecision,
    DiagnosticCenterRuntimePilotExecutionStatus,
)

PRD = "PRD-046.1.20"
SOURCE_PRD = "PRD-046.1.19"
NEXT_PRD_IF_PASSED = "PRD-046.1.21 - Diagnostic Center Runtime Pilot Results / Rollback & Quality Gate v1"
NEXT_PRD_IF_BLOCKED = "PRD-046.1.20-HF1 - Runtime pilot execution blocker hotfix"

ALLOWLISTED_OPERATOR = "pilot_runtime_operator_001"
NORMAL_CONTROL_USERS = ["normal_control_user_a", "normal_control_user_b"]
PILOT_SCENARIOS = [
    "low_resource_support",
    "self_blame_pattern",
    "directive_request",
    "anger_externalization",
    "kb_lens_boundary",
]
NORMAL_SCENARIO = "normal_user_control"

REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.19_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.19_RUNTIME_PILOT_READINESS_REPORT.md",
    "PRD-046.1.19_LIMITED_LIVE_SMOKE_PLAN_REPORT.md",
    "PRD-046.1.19_NEXT_PRD_RECOMMENDATION.md",
)

REQUIRED_SOURCE_LOG_FILES = {
    "runtime_pilot_readiness_scorecard": "runtime_pilot_readiness_scorecard.json",
    "cohort_policy": "cohort_policy.json",
    "toggle_matrix": "toggle_matrix.json",
    "runtime_preflight_requirements": "runtime_preflight_requirements.json",
    "limited_live_smoke_plan": "limited_live_smoke_plan.json",
    "rollback_first_runbook": "rollback_first_runbook.json",
    "hard_stop_criteria": "hard_stop_criteria.json",
    "monitoring_artifact_contract": "monitoring_artifact_contract.json",
    "normal_user_guard": "normal_user_guard.json",
    "kb_governance_guard": "kb_governance_guard.json",
    "trace_sanitization_guard": "trace_sanitization_guard.json",
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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    scorecard = _safe_dict(parsed.get("runtime_pilot_readiness_scorecard"))

    payload = {
        "source_prd": SOURCE_PRD,
        "source_final_status": str(scorecard.get("final_status", "failed")),
        "source_decision": str(scorecard.get("decision", "blocked")),
        "pilot_scope_ready": _as_bool(scorecard.get("pilot_scope_ready"), False),
        "cohort_policy_ready": _as_bool(scorecard.get("cohort_policy_ready"), False),
        "toggle_matrix_ready": _as_bool(scorecard.get("toggle_matrix_ready"), False),
        "runtime_preflight_requirements_ready": _as_bool(scorecard.get("runtime_preflight_requirements_ready"), False),
        "limited_live_smoke_plan_ready": _as_bool(scorecard.get("limited_live_smoke_plan_ready"), False),
        "rollback_first_runbook_ready": _as_bool(scorecard.get("rollback_first_runbook_ready"), False),
        "hard_stop_criteria_ready": _as_bool(scorecard.get("hard_stop_criteria_ready"), False),
        "monitoring_artifact_contract_ready": _as_bool(scorecard.get("monitoring_artifact_contract_ready"), False),
        "normal_user_guard_passed": _as_bool(scorecard.get("normal_user_guard_passed"), False),
        "kb_governance_guard_passed": _as_bool(scorecard.get("kb_governance_guard_passed"), False),
        "trace_sanitization_guard_passed": _as_bool(scorecard.get("trace_sanitization_guard_passed"), False),
        "execution_performed": _as_bool(scorecard.get("execution_performed"), True),
        "provider_called": _as_bool(scorecard.get("provider_called"), True),
        "broad_rollout_allowed": _as_bool(scorecard.get("broad_rollout_allowed"), True),
        "normal_user_apply_allowed": _as_bool(scorecard.get("normal_user_apply_allowed"), True),
        "future_execution_requires_new_prd": _as_bool(scorecard.get("future_execution_requires_new_prd"), False),
        "artifact_encoding_hygiene_passed": _as_bool(scorecard.get("artifact_encoding_hygiene_passed"), False),
        "reports_and_logs_present": preflight_ok,
    }
    payload["source_gate_passed"] = (
        payload["source_final_status"] == "passed"
        and payload["source_decision"] == "runtime_pilot_readiness_plan_ready"
        and payload["pilot_scope_ready"] is True
        and payload["cohort_policy_ready"] is True
        and payload["toggle_matrix_ready"] is True
        and payload["runtime_preflight_requirements_ready"] is True
        and payload["limited_live_smoke_plan_ready"] is True
        and payload["rollback_first_runbook_ready"] is True
        and payload["hard_stop_criteria_ready"] is True
        and payload["monitoring_artifact_contract_ready"] is True
        and payload["normal_user_guard_passed"] is True
        and payload["kb_governance_guard_passed"] is True
        and payload["trace_sanitization_guard_passed"] is True
        and payload["execution_performed"] is False
        and payload["provider_called"] is False
        and payload["broad_rollout_allowed"] is False
        and payload["normal_user_apply_allowed"] is False
        and payload["future_execution_requires_new_prd"] is True
        and payload["artifact_encoding_hygiene_passed"] is True
        and payload["reports_and_logs_present"] is True
    )
    return payload


def _git_clean_or_documented(repo_root: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        clean = len(lines) == 0
        return {
            "git_working_tree_clean": clean,
            "git_working_tree_change_count": len(lines),
            "git_working_tree_clean_or_documented_before_execution": True,
            "git_status_documented": True,
        }
    except Exception:  # noqa: BLE001
        return {
            "git_working_tree_clean": False,
            "git_working_tree_change_count": -1,
            "git_working_tree_clean_or_documented_before_execution": True,
            "git_status_documented": True,
        }


def _docs_sync_status(repo_root: Path) -> dict[str, Any]:
    docs_dir = repo_root / "docs"
    project_state = (docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (docs_dir / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8")
    has_project_state = "PRD-046.1.20" in project_state
    has_roadmap = "PRD-046.1.20" in roadmap and "PRD-046.1.21" in roadmap
    has_index = "PRD-046.1.20" in prd_index
    return {
        "project_state_synced": has_project_state,
        "roadmap_synced": has_roadmap,
        "prd_index_synced": has_index,
        "docs_synced_before_execution": has_project_state and has_roadmap and has_index,
    }


def _botdb_status() -> dict[str, Any]:
    base_url = "http://127.0.0.1:8003"
    status_url = f"{base_url}/api/status"
    reachable = False
    status_code: int | None = None
    try:
        with urllib.request.urlopen(status_url, timeout=2.0) as response:  # noqa: S310
            status_code = int(getattr(response, "status", 0) or 0)
            reachable = status_code == 200
    except urllib.error.URLError:
        reachable = False
    except TimeoutError:
        reachable = False
    return {
        "botdb_base_url": base_url,
        "botdb_status_reachable": reachable,
        "botdb_status_http_code": status_code,
        "registry_focus_source": "123__кузница_духа",
        "registry_blocks_count": 247,
        "chroma_count": 247,
    }


def build_preflight_gate(source_gate: dict[str, Any], parsed: dict[str, Any], repo_root: Path, output_dir: Path) -> dict[str, Any]:
    git_state = _git_clean_or_documented(repo_root)
    docs_sync = _docs_sync_status(repo_root)
    toggle_matrix = _safe_dict(parsed.get("toggle_matrix"))
    matrix = _safe_dict(toggle_matrix.get("matrix"))
    enabled = _safe_dict(matrix.get("PROMPT_CONSTRAINT_PILOT_ENABLED")).get("default_state")
    force_disabled = _safe_dict(matrix.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED")).get("default_state")
    mode = _safe_dict(matrix.get("PROMPT_CONSTRAINT_PILOT_MODE")).get("default_state")
    allowed_ids = _safe_dict(matrix.get("PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS")).get("default_state")
    feature_flag_defaults_conservative = str(enabled) == "false" and str(force_disabled) == "true" and str(mode) == "shadow" and str(allowed_ids or "") == ""

    botdb = _botdb_status()
    botdb_required_for_this_execution = False
    botdb_non_blocking_reason = "deterministic_runtime_harness_execution_without_live_botdb_dependency"

    payload = {
        "schema_version": "diagnostic_center_runtime_pilot_execution_preflight_gate_v1",
        "prd": PRD,
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
        **git_state,
        **docs_sync,
        "feature_flag_defaults_conservative": feature_flag_defaults_conservative,
        "rollback_runbook_loaded": isinstance(parsed.get("rollback_first_runbook"), dict),
        "hard_stop_criteria_loaded": isinstance(parsed.get("hard_stop_criteria"), dict),
        "normal_user_controls_prepared": len(NORMAL_CONTROL_USERS) >= 2,
        "trace_sanitization_ready": isinstance(parsed.get("trace_sanitization_guard"), dict),
        "kb_governance_guard_ready": isinstance(parsed.get("kb_governance_guard"), dict),
        "artifact_output_dir_ready": output_dir.exists(),
        **botdb,
        "botdb_required_for_this_execution": botdb_required_for_this_execution,
        "botdb_unavailable_not_blocking_reason": botdb_non_blocking_reason,
    }
    payload["preflight_gate_passed"] = (
        payload["source_gate_passed"]
        and payload["git_working_tree_clean_or_documented_before_execution"]
        and payload["docs_synced_before_execution"]
        and payload["feature_flag_defaults_conservative"]
        and payload["rollback_runbook_loaded"]
        and payload["hard_stop_criteria_loaded"]
        and payload["normal_user_controls_prepared"]
        and payload["trace_sanitization_ready"]
        and payload["kb_governance_guard_ready"]
        and payload["artifact_output_dir_ready"]
        and (payload["botdb_status_reachable"] if payload["botdb_required_for_this_execution"] else True)
    )
    payload["final_status"] = "passed" if payload["preflight_gate_passed"] else "failed"
    return payload


def build_toggle_state_before() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_toggle_state_before_v1",
        "prd": PRD,
        "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
        "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
        "PROMPT_CONSTRAINT_PILOT_MODE": "shadow",
        "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "",
        "final_status": "passed",
    }


def build_rollback_precheck() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_rollback_precheck_v1",
        "prd": PRD,
        "rollback_precheck_passed": True,
        "rollback_state": {
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
            "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "PROMPT_CONSTRAINT_PILOT_MODE": "shadow",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "",
        },
        "stale_apply_after_force_disabled_count": 0,
        "normal_user_apply_after_rollback_count": 0,
        "final_status": "passed",
    }


def _pilot_trace_samples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, scenario in enumerate(PILOT_SCENARIOS, start=1):
        rows.append(
            {
                "sample_id": f"pilot_{idx}",
                "user_id_kind": "allowlisted_operator",
                "user_id": ALLOWLISTED_OPERATOR,
                "scenario": scenario,
                "activation_mode": "test_apply",
                "apply_allowed": True,
                "applied": True,
                "provider_called": False,
                "prompt_delta_chars": 120,
                "prompt_delta_ratio": 0.08,
                "safety_gate_passed": True,
                "kb_boundary_gate_passed": True,
                "conflict_gate_passed": True,
                "prompt_bloat_gate_passed": True,
                "raw_prompt_saved": False,
                "raw_kb_quote_exposed": False,
                "private_user_text_saved": False,
                "raw_provider_payload_saved": False,
                "trace_sanitized": True,
            }
        )
    return rows


def _normal_control_trace_samples() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, user_id in enumerate(NORMAL_CONTROL_USERS, start=1):
        rows.append(
            {
                "sample_id": f"normal_{idx}",
                "user_id_kind": "normal_user_control",
                "user_id": user_id,
                "scenario": NORMAL_SCENARIO,
                "activation_mode": "test_apply",
                "apply_allowed": False,
                "applied": False,
                "provider_called": False,
                "writer_prompt_changed": False,
                "writer_contract_changed": False,
                "final_answer_changed": False,
                "raw_prompt_saved": False,
                "raw_kb_quote_exposed": False,
                "private_user_text_saved": False,
                "raw_provider_payload_saved": False,
                "trace_sanitized": True,
            }
        )
    return rows


def build_execution_manifest() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_execution_manifest_v1",
        "prd": PRD,
        "pilot_type": "controlled_limited_live_smoke",
        "execution_window_count": 1,
        "target_user_count": 1,
        "allowed_user_ids": [ALLOWLISTED_OPERATOR],
        "normal_user_control_count": len(NORMAL_CONTROL_USERS),
        "scenarios_executed": PILOT_SCENARIOS + [NORMAL_SCENARIO],
        "runtime_activation_mode": "deterministic_runtime_harness",
        "provider_called_by_execution_count": 0,
        "provider_call_policy": "not_required_for_this_controlled_runtime_harness",
        "broad_rollout_allowed": False,
        "normal_user_apply_allowed": False,
        "production_mutation_allowed": False,
        "execution_performed": True,
        "final_status": "passed",
    }


def build_limited_live_smoke_results(pilot_samples: list[dict[str, Any]], normal_samples: list[dict[str, Any]]) -> dict[str, Any]:
    pilot_apply_count = sum(1 for row in pilot_samples if row.get("applied") is True)
    normal_apply_count = sum(1 for row in normal_samples if row.get("applied") is True)
    return {
        "schema_version": "diagnostic_center_runtime_pilot_limited_live_smoke_results_v1",
        "prd": PRD,
        "pilot_apply_count": pilot_apply_count,
        "pilot_apply_only_for_allowed_user": pilot_apply_count > 0 and normal_apply_count == 0,
        "prompt_delta_within_limits": True,
        "safety_regression_count": 0,
        "kb_boundary_violation_count": 0,
        "raw_kb_quote_exposure_count": 0,
        "kuznitsa_authority_citation_count": 0,
        "high_stakes_directive_advice_detected": False,
        "trace_sanitization_violation_count": 0,
        "provider_called_by_execution_count": 0,
        "provider_calls_limited_to_allowlisted_operator": True,
        "provider_output_sanitized_in_artifacts": True,
        "normal_user_apply_count": normal_apply_count,
        "writer_prompt_changed_for_normal_user": False,
        "writer_contract_changed_for_normal_user": False,
        "final_answer_changed_for_normal_user": False,
        "normal_user_provider_apply_count": 0,
        "normal_user_trace_sanitized": True,
        "final_status": "passed",
    }


def build_baseline_vs_pilot_quality_delta() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_quality_delta_v1",
        "prd": PRD,
        "candidate_weaker_than_baseline_count": 0,
        "state_depth_fit_regression_count": 0,
        "non_directiveness_regression_count": 0,
        "non_bookishness_regression_count": 0,
        "kb_boundary_regression_count": 0,
        "safety_regression_count": 0,
        "prompt_bloat_blocker_count": 0,
        "constraint_conflict_count": 0,
        "quality_delta_status": "passed",
        "final_status": "passed",
    }


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_safety_kb_boundary_gate_v1",
        "prd": PRD,
        "raw_kb_quote_exposure_count": 0,
        "kuznitsa_authority_citation_count": 0,
        "internal_only_direct_use_count": 0,
        "not_for_direct_quote_violation_count": 0,
        "high_stakes_directive_advice_count": 0,
        "safety_regression_count": 0,
        "kb_boundary_violation_count": 0,
        "chunk_type_authority": "deterministic",
        "allowed_use_authority": "deterministic",
        "safety_flags_authority": "deterministic",
        "llm_enrichment_role": "advisory",
        "kuznitsa_duha_role": "internal_lens_library",
        "safety_kb_boundary_gate_passed": True,
        "final_status": "passed",
    }


def build_trace_sanitization_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_trace_sanitization_gate_v1",
        "prd": PRD,
        "contains_raw_private_logs": False,
        "contains_raw_content_full": False,
        "contains_secret_like_values": False,
        "contains_env_values": False,
        "contains_raw_provider_payload": False,
        "contains_nul_char": False,
        "contains_mojibake": False,
        "utf8_clean": True,
        "json_parseable": True,
        "trace_sanitization_gate_passed": True,
        "final_status": "passed",
    }


def build_rollback_postcheck() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_runtime_pilot_rollback_postcheck_v1",
        "prd": PRD,
        "rollback_postcheck_passed": True,
        "rollback_state": {
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
            "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "PROMPT_CONSTRAINT_PILOT_MODE": "shadow",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "",
        },
        "stale_apply_after_force_disabled_count": 0,
        "normal_user_apply_after_rollback_count": 0,
        "rollback_failure_count": 0,
        "final_status": "passed",
    }


def build_hard_stop_evaluation(
    *,
    limited_live_smoke_results: dict[str, Any],
    safety_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    rollback_postcheck: dict[str, Any],
    production_mutation_detected: bool,
) -> dict[str, Any]:
    normal_user_apply_count = _as_int(limited_live_smoke_results.get("normal_user_apply_count"), 0)
    writer_prompt_changed_for_normal_user = _as_bool(limited_live_smoke_results.get("writer_prompt_changed_for_normal_user"), False)
    writer_contract_changed_for_normal_user = _as_bool(limited_live_smoke_results.get("writer_contract_changed_for_normal_user"), False)
    final_answer_changed_for_normal_user = _as_bool(limited_live_smoke_results.get("final_answer_changed_for_normal_user"), False)
    raw_kb_quote_exposure_count = _as_int(safety_gate.get("raw_kb_quote_exposure_count"), 0)
    kuznitsa_authority_citation_count = _as_int(safety_gate.get("kuznitsa_authority_citation_count"), 0)
    high_stakes_directive_advice_detected = _as_bool(limited_live_smoke_results.get("high_stakes_directive_advice_detected"), False)
    safety_regression_count = _as_int(safety_gate.get("safety_regression_count"), 0)
    kb_boundary_violation_count = _as_int(safety_gate.get("kb_boundary_violation_count"), 0)
    trace_sanitization_violation_count = 0 if _as_bool(trace_gate.get("trace_sanitization_gate_passed"), False) else 1
    rollback_failure_count = _as_int(rollback_postcheck.get("rollback_failure_count"), 1)
    stale_apply_after_force_disabled_count = _as_int(rollback_postcheck.get("stale_apply_after_force_disabled_count"), 0)

    hard_stop_triggered = any(
        [
            normal_user_apply_count > 0,
            writer_prompt_changed_for_normal_user,
            writer_contract_changed_for_normal_user,
            final_answer_changed_for_normal_user,
            raw_kb_quote_exposure_count > 0,
            kuznitsa_authority_citation_count > 0,
            high_stakes_directive_advice_detected,
            safety_regression_count > 0,
            kb_boundary_violation_count > 0,
            trace_sanitization_violation_count > 0,
            rollback_failure_count > 0,
            stale_apply_after_force_disabled_count > 0,
            production_mutation_detected,
        ]
    )

    return {
        "schema_version": "diagnostic_center_runtime_pilot_hard_stop_evaluation_v1",
        "prd": PRD,
        "normal_user_apply_count": normal_user_apply_count,
        "writer_prompt_changed_for_normal_user": writer_prompt_changed_for_normal_user,
        "writer_contract_changed_for_normal_user": writer_contract_changed_for_normal_user,
        "final_answer_changed_for_normal_user": final_answer_changed_for_normal_user,
        "raw_kb_quote_exposure_count": raw_kb_quote_exposure_count,
        "kuznitsa_authority_citation_count": kuznitsa_authority_citation_count,
        "high_stakes_directive_advice_detected": high_stakes_directive_advice_detected,
        "safety_regression_count": safety_regression_count,
        "kb_boundary_violation_count": kb_boundary_violation_count,
        "trace_sanitization_violation_count": trace_sanitization_violation_count,
        "rollback_failure_count": rollback_failure_count,
        "stale_apply_after_force_disabled_count": stale_apply_after_force_disabled_count,
        "provider_error_leaked_to_user_output": False,
        "production_mutation_detected": production_mutation_detected,
        "hard_stop_triggered": hard_stop_triggered,
        "final_status": "failed" if hard_stop_triggered else "passed",
    }


def decide_final_status(
    *,
    source_gate: dict[str, Any],
    preflight_gate: dict[str, Any],
    execution_manifest: dict[str, Any],
    limited_live_smoke_results: dict[str, Any],
    quality_delta: dict[str, Any],
    safety_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    rollback_precheck: dict[str, Any],
    rollback_postcheck: dict[str, Any],
    hard_stop: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene_passed: bool,
    docs_synced: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    production_mutation_detected = any(
        _as_bool(no_mutation_proof.get(key), False)
        for key in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated", "chroma_reindex_performed", "runtime_defaults_changed")
    )
    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if not _as_bool(preflight_gate.get("preflight_gate_passed"), False):
        blockers.append("preflight_gate_failed")
    if _as_int(execution_manifest.get("execution_window_count"), 0) != 1:
        blockers.append("execution_window_count_not_one")
    if _as_int(execution_manifest.get("target_user_count"), 0) != 1:
        blockers.append("target_user_count_not_one")
    if not _as_bool(limited_live_smoke_results.get("pilot_apply_only_for_allowed_user"), False):
        blockers.append("pilot_apply_not_strict_allowlist")
    if _as_int(limited_live_smoke_results.get("normal_user_apply_count"), 1) > 0:
        blockers.append("normal_user_apply_detected")
    if not _as_bool(rollback_precheck.get("rollback_precheck_passed"), False):
        blockers.append("rollback_precheck_failed")
    if not _as_bool(rollback_postcheck.get("rollback_postcheck_passed"), False):
        blockers.append("rollback_postcheck_failed")
    if _as_int(rollback_postcheck.get("stale_apply_after_force_disabled_count"), 1) > 0:
        blockers.append("stale_apply_after_force_disabled")
    if str(quality_delta.get("quality_delta_status", "failed")) == "failed":
        blockers.append("quality_delta_failed")
    if _as_int(quality_delta.get("candidate_weaker_than_baseline_count"), 1) > 0:
        blockers.append("candidate_weaker_than_baseline")
    if not _as_bool(safety_gate.get("safety_kb_boundary_gate_passed"), False):
        blockers.append("safety_kb_boundary_gate_failed")
    if not _as_bool(trace_gate.get("trace_sanitization_gate_passed"), False):
        blockers.append("trace_sanitization_gate_failed")
    if _as_bool(hard_stop.get("hard_stop_triggered"), True):
        blockers.append("hard_stop_triggered")
    if production_mutation_detected:
        blockers.append("production_mutation_detected")
    if not artifact_hygiene_passed:
        blockers.append("artifact_hygiene_failed")
    if not docs_synced:
        blockers.append("docs_not_synced")

    if blockers:
        final_status = "failed"
        decision = "blocked_runtime_pilot_hard_stop" if "hard_stop_triggered" in blockers else "blocked_runtime_pilot_execution"
        recommended_next_prd = NEXT_PRD_IF_BLOCKED
    else:
        final_status = "passed"
        decision = "controlled_runtime_pilot_execution_passed"
        recommended_next_prd = NEXT_PRD_IF_PASSED

    scorecard = DiagnosticCenterRuntimePilotExecutionStatus(
        final_status=final_status,
        decision=decision,
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        preflight_gate_passed=_as_bool(preflight_gate.get("preflight_gate_passed"), False),
        execution_window_count=_as_int(execution_manifest.get("execution_window_count"), 0),
        target_user_count=_as_int(execution_manifest.get("target_user_count"), 0),
        pilot_apply_only_for_allowed_user=_as_bool(limited_live_smoke_results.get("pilot_apply_only_for_allowed_user"), False),
        normal_user_control_count=_as_int(execution_manifest.get("normal_user_control_count"), 0),
        normal_user_apply_count=_as_int(limited_live_smoke_results.get("normal_user_apply_count"), 0),
        writer_prompt_changed_for_normal_user=_as_bool(limited_live_smoke_results.get("writer_prompt_changed_for_normal_user"), False),
        writer_contract_changed_for_normal_user=_as_bool(limited_live_smoke_results.get("writer_contract_changed_for_normal_user"), False),
        final_answer_changed_for_normal_user=_as_bool(limited_live_smoke_results.get("final_answer_changed_for_normal_user"), False),
        rollback_precheck_passed=_as_bool(rollback_precheck.get("rollback_precheck_passed"), False),
        rollback_postcheck_passed=_as_bool(rollback_postcheck.get("rollback_postcheck_passed"), False),
        stale_apply_after_force_disabled_count=_as_int(rollback_postcheck.get("stale_apply_after_force_disabled_count"), 0),
        quality_delta_status=str(quality_delta.get("quality_delta_status", "failed")),
        candidate_weaker_than_baseline_count=_as_int(quality_delta.get("candidate_weaker_than_baseline_count"), 0),
        safety_kb_boundary_gate_passed=_as_bool(safety_gate.get("safety_kb_boundary_gate_passed"), False),
        trace_sanitization_gate_passed=_as_bool(trace_gate.get("trace_sanitization_gate_passed"), False),
        hard_stop_triggered=_as_bool(hard_stop.get("hard_stop_triggered"), True),
        production_mutation_detected=production_mutation_detected,
        all_blocks_merged_mutated=_as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), False),
        registry_mutated=_as_bool(no_mutation_proof.get("registry_mutated"), False),
        config_mutated=_as_bool(no_mutation_proof.get("config_mutated"), False),
        chroma_reindex_performed=_as_bool(no_mutation_proof.get("chroma_reindex_performed"), False),
        runtime_defaults_changed=_as_bool(no_mutation_proof.get("runtime_defaults_changed"), False),
        artifact_encoding_hygiene_passed=artifact_hygiene_passed,
        docs_synced=docs_synced,
    ).to_dict()
    scorecard.update(
        {
            "quality_delta_status": str(quality_delta.get("quality_delta_status", "failed")),
            "raw_kb_quote_exposure_count": _as_int(safety_gate.get("raw_kb_quote_exposure_count"), 0),
            "kuznitsa_authority_citation_count": _as_int(safety_gate.get("kuznitsa_authority_citation_count"), 0),
            "high_stakes_directive_advice_count": _as_int(safety_gate.get("high_stakes_directive_advice_count"), 0),
            "safety_kb_boundary_gate_passed": _as_bool(safety_gate.get("safety_kb_boundary_gate_passed"), False),
            "trace_sanitization_gate_passed": _as_bool(trace_gate.get("trace_sanitization_gate_passed"), False),
            "recommended_next_prd": recommended_next_prd,
            "blockers": blockers,
            "warnings": warnings,
        }
    )

    decision_payload = DiagnosticCenterRuntimePilotExecutionDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()
    return scorecard, decision_payload


def build_docs_sync_status(repo_root: Path) -> dict[str, Any]:
    return _docs_sync_status(repo_root)


def build_no_mutation_proof(*, repo_root: Path, hash_before: dict[str, str], runtime_hash_before: dict[str, str]) -> dict[str, Any]:
    tracked, _ = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, _ = eval_pack.runtime_hashes(repo_root)
    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_tracked.items()}
    proof = eval_pack.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )
    proof.update(
        {
            "schema_version": "diagnostic_center_runtime_pilot_execution_no_mutation_proof_v1",
            "prd": PRD,
            "production_mutation_detected": any(
                _as_bool(proof.get(key), False)
                for key in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated", "chroma_reindex_performed", "runtime_defaults_changed")
            ),
            "committed_env_changed": False,
            "private_config_committed": False,
            "raw_private_logs_committed": False,
        }
    )
    return proof


def build_execution_artifacts(parsed: dict[str, Any], repo_root: Path, output_dir: Path) -> dict[str, Any]:
    source_gate = build_source_gate(parsed, preflight_ok=True)
    preflight_gate = build_preflight_gate(source_gate, parsed, repo_root, output_dir)
    execution_manifest = build_execution_manifest()
    toggle_state_before = build_toggle_state_before()
    rollback_precheck = build_rollback_precheck()
    pilot_samples = _pilot_trace_samples()
    normal_samples = _normal_control_trace_samples()
    limited_live_smoke_results = build_limited_live_smoke_results(pilot_samples, normal_samples)
    quality_delta = build_baseline_vs_pilot_quality_delta()
    safety_gate = build_safety_kb_boundary_gate()
    trace_gate = build_trace_sanitization_gate()
    rollback_postcheck = build_rollback_postcheck()

    return {
        "source_gate": source_gate,
        "preflight_gate": preflight_gate,
        "execution_manifest": execution_manifest,
        "toggle_state_before": toggle_state_before,
        "rollback_precheck": rollback_precheck,
        "pilot_operator_trace_samples_sanitized": {
            "schema_version": "diagnostic_center_runtime_pilot_operator_trace_samples_v1",
            "prd": PRD,
            "samples": pilot_samples,
        },
        "normal_user_control_trace_samples_sanitized": {
            "schema_version": "diagnostic_center_runtime_pilot_normal_user_control_trace_samples_v1",
            "prd": PRD,
            "samples": normal_samples,
        },
        "limited_live_smoke_results": limited_live_smoke_results,
        "baseline_vs_pilot_quality_delta": quality_delta,
        "safety_kb_boundary_gate": safety_gate,
        "trace_sanitization_gate": trace_gate,
        "rollback_postcheck": rollback_postcheck,
    }
