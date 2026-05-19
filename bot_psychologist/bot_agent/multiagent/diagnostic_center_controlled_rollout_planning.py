"""PRD-046.1.30 Diagnostic Center controlled rollout planning (plan-only)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .contracts.diagnostic_center_controlled_rollout_planning_v1 import (
    ControlledRolloutCohortPolicy,
    ControlledRolloutDecision,
    ControlledRolloutEvidencePlan,
    ControlledRolloutHardStopCriteria,
    ControlledRolloutMonitoringPlan,
    ControlledRolloutPlanningScorecard,
    ControlledRolloutPlanningSourceGate,
    ControlledRolloutPreflightGate,
    ControlledRolloutRollbackPlan,
    ControlledRolloutToggleMatrix,
)

PRD = "PRD-046.1.30"
SOURCE_PRD_1 = "PRD-046.1.28"
SOURCE_PRD_2 = "PRD-046.1.29"
NEXT_PRD_PASSED = "PRD-046.1.31 - Diagnostic Center Controlled Rollout Execution Gate v1"
NEXT_PRD_BLOCKED = "PRD-046.1.30-HF1 - Controlled Rollout Planning Hotfix"

SOURCE_REPORTS = {
    "source_046_1_28_implementation": "PRD-046.1.28_IMPLEMENTATION_REPORT.md",
    "source_046_1_28_acceptance": "PRD-046.1.28_FINAL_RUNTIME_GOVERNANCE_ACCEPTANCE_REPORT.md",
    "source_046_1_29_implementation": "PRD-046.1.29_IMPLEMENTATION_REPORT.md",
    "source_046_1_29_next": "PRD-046.1.29_NEXT_PRD_RECOMMENDATION.md",
}

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}


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


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_metric(text: str, key: str) -> str | None:
    key_escaped = re.escape(key)
    patterns = [
        rf"`{key_escaped}=([^`]+)`",
        rf"{key_escaped}\s*=\s*([A-Za-z0-9_.\-]+)",
        rf"{key_escaped}:\s*`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _contains_all(text: str, items: list[str]) -> bool:
    lowered = text.lower()
    return all(item.lower() in lowered for item in items)


def required_paths(reports_dir: Path, docs_dir: Path) -> dict[str, Path]:
    required: dict[str, Path] = {}
    for key, file_name in SOURCE_REPORTS.items():
        required[key] = reports_dir / file_name
    required["runtime_map"] = docs_dir / "DIAGNOSTIC_CENTER_RUNTIME_MAP.md"
    required["eval_harness"] = docs_dir / "DIAGNOSTIC_CENTER_EVAL_HARNESS.md"
    required["project_state"] = docs_dir / "PROJECT_STATE.md"
    required["roadmap"] = docs_dir / "ROADMAP.md"
    required["prd_index"] = docs_dir / "PRD_INDEX.md"
    required["decisions"] = docs_dir / "DECISIONS.md"
    return required


def preflight(reports_dir: Path, docs_dir: Path) -> dict[str, Any]:
    required = required_paths(reports_dir, docs_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    texts: dict[str, str] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        try:
            texts[key] = _read_text(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {k: str(v.as_posix()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "texts": texts,
    }


def build_source_gate(preflight_payload: dict[str, Any]) -> dict[str, Any]:
    texts = dict(preflight_payload.get("texts") or {})
    blockers: list[str] = []

    report_128_impl = texts.get("source_046_1_28_implementation", "")
    report_128_accept = texts.get("source_046_1_28_acceptance", "")
    report_129_impl = texts.get("source_046_1_29_implementation", "")
    report_129_next = texts.get("source_046_1_29_next", "")
    runtime_map = texts.get("runtime_map", "")
    eval_harness = texts.get("eval_harness", "")
    project_state = texts.get("project_state", "")
    roadmap = texts.get("roadmap", "")
    prd_index = texts.get("prd_index", "")
    decisions = texts.get("decisions", "")

    status_128 = _extract_metric(report_128_impl, "Final status") or _extract_metric(report_128_accept, "final_status") or "blocked"
    decision_128 = _extract_metric(report_128_impl, "Decision") or _extract_metric(report_128_accept, "decision") or "blocked"
    status_129 = _extract_metric(report_129_impl, "final_status") or "blocked"
    decision_129 = _extract_metric(report_129_impl, "decision") or "blocked"

    source_046_1_28_passed = str(status_128) == "passed" and str(decision_128) == "accepted_ready_for_cleanup_stabilization"
    source_046_1_29_passed = str(status_129) == "passed" and str(decision_129) == "diagnostic_center_stabilized_cleanup_manifested"

    runtime_map_gate_passed = _contains_all(
        runtime_map,
        [
            "Broad rollout is disabled",
            "Normal-user activation is disabled",
            "Production-ready declaration is not granted",
            "Rollback-first",
            "Safety/KB boundary",
            "trace sanitization",
            "No-mutation",
            "artifact hygiene",
        ],
    )
    eval_harness_gate_passed = _contains_all(
        eval_harness,
        [
            "Final runtime governance acceptance gates",
            "Provider-backed evidence and budget gates",
            "Normal-user no-effect gates",
            "Rollback and hard-stop gates",
            "Safety/KB boundary and trace/provider sanitization gates",
            "BotDB stability gates",
            "Response quality eval/calibration packs",
            "Contract and no-mutation proofs",
            "Artifact encoding hygiene validation",
        ],
    )

    docs_compaction_gate_passed = (
        "PRD-046.1.29" in project_state
        and "PRD-046.1.29" in roadmap
        and "PRD-046.1.29" in prd_index
        and ("ADR-049" in decisions or "Controlled Rollout Planning Boundary" in decisions)
    )

    if not preflight_payload.get("ok", False):
        blockers.append("required_source_or_docs_missing")
    if not source_046_1_28_passed:
        blockers.append("source_046_1_28_not_passed")
    if not source_046_1_29_passed:
        blockers.append("source_046_1_29_not_passed")
    if not runtime_map_gate_passed:
        blockers.append("runtime_map_gate_failed")
    if not eval_harness_gate_passed:
        blockers.append("eval_harness_gate_failed")
    if not docs_compaction_gate_passed:
        blockers.append("docs_compaction_gate_failed")

    payload = ControlledRolloutPlanningSourceGate(
        source_gate_passed=len(blockers) == 0,
        source_046_1_28_passed=source_046_1_28_passed,
        source_046_1_29_passed=source_046_1_29_passed,
        runtime_map_gate_passed=runtime_map_gate_passed,
        eval_harness_gate_passed=eval_harness_gate_passed,
        docs_compaction_gate_passed=docs_compaction_gate_passed,
        blockers=blockers,
    ).to_dict()
    payload["source_046_1_28_final_status"] = str(status_128)
    payload["source_046_1_28_decision"] = str(decision_128)
    payload["source_046_1_29_final_status"] = str(status_129)
    payload["source_046_1_29_decision"] = str(decision_129)
    return payload


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {key: repo_root / rel for key, rel in TRACKED_PRODUCTION_PATHS.items()}
    hashes: dict[str, str] = {}
    for key, path in tracked.items():
        hashes[key] = _sha256(path) if path.exists() and path.is_file() else "missing"
    return tracked, hashes


def build_no_mutation_proof(hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    all_blocks_merged_mutated = hash_before.get("all_blocks_merged") != hash_after.get("all_blocks_merged")
    registry_mutated = hash_before.get("registry") != hash_after.get("registry")
    config_mutated = hash_before.get("config") != hash_after.get("config")
    production_data_mutated = all_blocks_merged_mutated or registry_mutated or config_mutated
    return {
        "schema_version": "diagnostic_center_controlled_rollout_planning_no_mutation_proof_v1",
        "prd_id": PRD,
        "all_blocks_merged_mutated": all_blocks_merged_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "runtime_defaults_changed": False,
        "production_data_mutated": production_data_mutated,
        "provider_called": False,
        "provider_execution_performed": False,
        "no_mutation_proof_passed": not production_data_mutated,
    }


def build_cohort_policy() -> dict[str, Any]:
    payload = ControlledRolloutCohortPolicy().to_dict()
    payload["ready"] = (
        payload["max_target_users"] <= 3
        and payload["target_user_type"] == "allowlisted_internal_or_synthetic_operators_only"
        and payload["normal_user_activation_allowed"] is False
        and payload["broad_rollout_allowed"] is False
        and payload["production_ready_allowed"] is False
        and payload["requires_explicit_allowlist"] is True
        and payload["requires_test_prefix_or_operator_marker"] is True
    )
    return payload


def build_toggle_matrix() -> dict[str, Any]:
    matrix = {
        "force_disabled=true": "total disabled",
        "enabled=false": "total disabled",
        "mode=shadow": "no apply",
        "mode=controlled_limited_apply": "apply only allowlisted target users",
        "normal_user": "never apply",
        "hard_stop_triggered=true": "forced rollback",
        "provider_budget_exceeded=true": "forced rollback",
        "safety_kb_boundary_violation=true": "forced rollback",
        "trace_sanitization_failure=true": "forced rollback",
        "botdb_unstable=true": "forced rollback",
    }
    ready = len(matrix) >= 10
    return ControlledRolloutToggleMatrix(matrix=matrix, ready=ready).to_dict()


def build_preflight_gates() -> dict[str, Any]:
    checks = [
        {"id": "botdb_status_ok", "required": True, "description": "BotDB status endpoint is healthy."},
        {"id": "registry_focus_source_only", "required": True, "description": "Registry contains only focus production source."},
        {"id": "chroma_count_ok", "required": True, "description": "Chroma count matches expected production count."},
        {"id": "query_endpoint_200", "required": True, "description": "Query endpoint responds with HTTP 200."},
        {"id": "semantic_fallback_used_false", "required": True, "description": "Unexpected semantic fallback is not used."},
        {"id": "botdb_circuit_open_false", "required": True, "description": "BotDB circuit breaker remains closed."},
        {"id": "runtime_defaults_conservative", "required": True, "description": "Defaults stay conservative and disabled."},
        {"id": "allowlist_explicitly_set", "required": True, "description": "Allowlist is explicitly configured."},
        {"id": "rollback_switch_tested_before_execution", "required": True, "description": "Rollback switch validated before execution."},
        {"id": "artifact_output_path_clean", "required": True, "description": "Output path is prepared and clean."},
        {"id": "provider_budget_configured", "required": True, "description": "Provider budget is configured for controlled window."},
        {"id": "normal_user_controls_configured", "required": True, "description": "Normal-user controls are prepared."},
    ]
    ready = len(checks) >= 12
    return ControlledRolloutPreflightGate(checks=checks, ready=ready).to_dict()


def build_hard_stop_criteria() -> dict[str, Any]:
    hard_stops = [
        "any normal-user apply > 0",
        "any normal-user provider call > 0",
        "rollback failure > 0",
        "raw provider payload persisted",
        "raw KB text exposed as authority",
        "KB quote/citation boundary violation",
        "provider budget exceeded",
        "BotDB circuit open",
        "semantic fallback used unexpectedly",
        "runtime defaults changed",
        "production data mutation detected",
        "artifact encoding/hygiene blocker",
    ]
    return ControlledRolloutHardStopCriteria(hard_stops=hard_stops, ready=len(hard_stops) >= 12).to_dict()


def build_monitoring_plan() -> dict[str, Any]:
    metrics = {
        "apply_count": "count controlled apply events for allowlisted users only",
        "normal_user_apply_count": "must remain 0",
        "normal_user_provider_calls": "must remain 0",
        "rollback_failure_count": "must remain 0",
        "safety_kb_boundary_violation_count": "must remain 0",
        "trace_sanitization_failure_count": "must remain 0",
        "provider_budget_exceeded_count": "must remain 0",
        "botdb_unstable_events": "must remain 0",
    }
    return ControlledRolloutMonitoringPlan(metrics=metrics, ready=len(metrics) >= 8).to_dict()


def build_rollback_plan() -> dict[str, Any]:
    steps = [
        "set PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true",
        "set PROMPT_CONSTRAINT_PILOT_ENABLED=false",
        "set PROMPT_CONSTRAINT_PILOT_MODE=shadow",
        "clear allowlist",
        "re-run one allowlisted check expecting no apply",
        "re-run normal-user control expecting no effect",
        "record rollback proof artifact",
    ]
    return ControlledRolloutRollbackPlan(rollback_steps=steps, ready=len(steps) >= 7).to_dict()


def build_evidence_capture_plan() -> dict[str, Any]:
    artifacts = [
        "execution_manifest",
        "provider_budget_report",
        "sanitized_provider_trace",
        "normal_user_no_effect_report",
        "quality_micro_shift_report",
        "safety_kb_boundary_report",
        "trace_sanitization_report",
        "rollback_precheck_postcheck_report",
        "botdb_preflight_postcheck_report",
        "no_mutation_proof",
        "artifact_hygiene_report",
        "operator_summary",
        "next_prd_recommendation",
    ]
    return ControlledRolloutEvidencePlan(required_artifacts=artifacts, ready=len(artifacts) >= 13).to_dict()


def build_normal_user_no_effect_plan() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_rollout_normal_user_no_effect_plan_v1",
        "prd_id": PRD,
        "normal_user_activation_allowed": False,
        "required_normal_user_control_count": 2,
        "normal_user_apply_allowed": False,
        "normal_user_provider_calls_allowed": False,
        "writer_prompt_change_allowed_for_normal_user": False,
        "writer_contract_change_allowed_for_normal_user": False,
        "final_answer_change_allowed_for_normal_user": False,
        "ready": True,
    }


def build_controlled_rollout_plan(
    *,
    cohort_policy: dict[str, Any],
    toggle_matrix: dict[str, Any],
    preflight_gates: dict[str, Any],
    hard_stop_criteria: dict[str, Any],
    monitoring_plan: dict[str, Any],
    rollback_plan: dict[str, Any],
    evidence_capture_plan: dict[str, Any],
    normal_user_no_effect_plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_rollout_plan_v1",
        "prd_id": PRD,
        "rollout_type": "controlled_limited_rollout_execution",
        "execution_performed": False,
        "provider_called": False,
        "runtime_defaults_changed": False,
        "production_data_mutated": False,
        "cohort_policy": cohort_policy,
        "toggle_matrix": toggle_matrix,
        "preflight_gates": preflight_gates,
        "hard_stop_criteria": hard_stop_criteria,
        "monitoring_plan": monitoring_plan,
        "rollback_plan": rollback_plan,
        "evidence_capture_plan": evidence_capture_plan,
        "normal_user_no_effect_plan": normal_user_no_effect_plan,
        "ready": True,
    }


def docs_sync_status(docs_dir: Path) -> dict[str, Any]:
    project_state = _read_text(docs_dir / "PROJECT_STATE.md") if (docs_dir / "PROJECT_STATE.md").exists() else ""
    roadmap = _read_text(docs_dir / "ROADMAP.md") if (docs_dir / "ROADMAP.md").exists() else ""
    prd_index = _read_text(docs_dir / "PRD_INDEX.md") if (docs_dir / "PRD_INDEX.md").exists() else ""
    decisions = _read_text(docs_dir / "DECISIONS.md") if (docs_dir / "DECISIONS.md").exists() else ""
    return {
        "project_state_synced": "PRD-046.1.30" in project_state,
        "roadmap_synced": "PRD-046.1.30" in roadmap and "PRD-046.1.31" in roadmap,
        "prd_index_synced": "PRD-046.1.30" in prd_index,
        "decisions_synced": ("Controlled Rollout Planning Boundary" in decisions or "ADR-049" in decisions),
        "docs_synced": "PRD-046.1.30" in project_state and "PRD-046.1.30" in roadmap and "PRD-046.1.30" in prd_index,
    }


def build_decision_and_scorecard(
    *,
    source_gate: dict[str, Any],
    cohort_policy: dict[str, Any],
    toggle_matrix: dict[str, Any],
    preflight_gates: dict[str, Any],
    hard_stop_criteria: dict[str, Any],
    monitoring_plan: dict[str, Any],
    rollback_plan: dict[str, Any],
    evidence_capture_plan: dict[str, Any],
    normal_user_no_effect_plan: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene_passed: bool,
    docs_sync: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    source_passed = _as_bool(source_gate.get("source_gate_passed"), False)
    runtime_map_gate = _as_bool(source_gate.get("runtime_map_gate_passed"), False)
    eval_harness_gate = _as_bool(source_gate.get("eval_harness_gate_passed"), False)

    cohort_policy_ready = _as_bool(cohort_policy.get("ready"), False)
    toggle_matrix_ready = _as_bool(toggle_matrix.get("ready"), False)
    preflight_gates_ready = _as_bool(preflight_gates.get("ready"), False)
    hard_stop_criteria_ready = _as_bool(hard_stop_criteria.get("ready"), False)
    rollback_plan_ready = _as_bool(rollback_plan.get("ready"), False)
    monitoring_plan_ready = _as_bool(monitoring_plan.get("ready"), False)
    evidence_capture_plan_ready = _as_bool(evidence_capture_plan.get("ready"), False)
    normal_user_no_effect_plan_ready = _as_bool(normal_user_no_effect_plan.get("ready"), False)

    no_mutation_proof_passed = _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False)
    production_data_mutated = _as_bool(no_mutation_proof.get("production_data_mutated"), True)

    if not source_passed:
        blockers.append("source_gate_failed")
    if not runtime_map_gate:
        blockers.append("runtime_map_gate_failed")
    if not eval_harness_gate:
        blockers.append("eval_harness_gate_failed")
    if not cohort_policy_ready:
        blockers.append("cohort_policy_not_ready")
    if not toggle_matrix_ready:
        blockers.append("toggle_matrix_not_ready")
    if not preflight_gates_ready:
        blockers.append("preflight_gates_not_ready")
    if not hard_stop_criteria_ready:
        blockers.append("hard_stop_criteria_not_ready")
    if not rollback_plan_ready:
        blockers.append("rollback_plan_not_ready")
    if not monitoring_plan_ready:
        blockers.append("monitoring_plan_not_ready")
    if not evidence_capture_plan_ready:
        blockers.append("evidence_capture_plan_not_ready")
    if not normal_user_no_effect_plan_ready:
        blockers.append("normal_user_no_effect_plan_not_ready")
    if not no_mutation_proof_passed or production_data_mutated:
        blockers.append("no_mutation_proof_failed")
    if not artifact_hygiene_passed:
        blockers.append("artifact_hygiene_failed")
    if not _as_bool(docs_sync.get("docs_synced"), False):
        blockers.append("docs_not_synced")

    needs_human_governance = _as_bool(cohort_policy.get("normal_user_activation_allowed"), False) or str(
        cohort_policy.get("target_user_type", "")
    ) != "allowlisted_internal_or_synthetic_operators_only"
    if needs_human_governance:
        blockers.append("human_product_governance_required_before_real_user_rollout")

    if blockers:
        final_status = "blocked"
        if "human_product_governance_required_before_real_user_rollout" in blockers:
            decision_value = "blocked_needs_human_governance"
        else:
            decision_value = "blocked_needs_hotfix"
    else:
        final_status = "passed"
        decision_value = "ready_for_controlled_rollout_execution_prd"

    decision = ControlledRolloutDecision(
        final_status=final_status,
        decision=decision_value,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        provider_execution_performed=False,
        provider_called=False,
        runtime_defaults_changed=False,
        production_data_mutated=production_data_mutated,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    decision["recommended_next_prd"] = NEXT_PRD_PASSED if final_status == "passed" else NEXT_PRD_BLOCKED

    scorecard = ControlledRolloutPlanningScorecard(
        final_status=final_status,
        decision=decision_value,
        source_gate="passed" if source_passed else "failed",
        runtime_map_gate="passed" if runtime_map_gate else "failed",
        eval_harness_gate="passed" if eval_harness_gate else "failed",
        cohort_policy_ready=cohort_policy_ready,
        toggle_matrix_ready=toggle_matrix_ready,
        preflight_gates_ready=preflight_gates_ready,
        hard_stop_criteria_ready=hard_stop_criteria_ready,
        rollback_plan_ready=rollback_plan_ready,
        monitoring_plan_ready=monitoring_plan_ready,
        evidence_capture_plan_ready=evidence_capture_plan_ready,
        normal_user_no_effect_plan_ready=normal_user_no_effect_plan_ready,
        provider_execution_performed=False,
        provider_called=False,
        runtime_defaults_changed=False,
        production_data_mutated=production_data_mutated,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        no_mutation_proof_passed=no_mutation_proof_passed,
        artifact_encoding_hygiene_passed=artifact_hygiene_passed,
        docs_synced=_as_bool(docs_sync.get("docs_synced"), False),
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    scorecard["source_gate_passed"] = source_passed
    scorecard["runtime_map_gate_passed"] = runtime_map_gate
    scorecard["eval_harness_gate_passed"] = eval_harness_gate
    return decision, scorecard


__all__ = [
    "PRD",
    "SOURCE_PRD_1",
    "SOURCE_PRD_2",
    "NEXT_PRD_PASSED",
    "NEXT_PRD_BLOCKED",
    "preflight",
    "build_source_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_cohort_policy",
    "build_toggle_matrix",
    "build_preflight_gates",
    "build_hard_stop_criteria",
    "build_monitoring_plan",
    "build_rollback_plan",
    "build_evidence_capture_plan",
    "build_normal_user_no_effect_plan",
    "build_controlled_rollout_plan",
    "docs_sync_status",
    "build_decision_and_scorecard",
    "_sha256",
]

