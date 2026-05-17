"""PRD-046.1.12 production-limited rollout planning gate (plan-only, provider-free)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_production_limited_rollout_plan_v1 import (
    PromptConstraintProductionLimitedAbortCriteriaV1,
    PromptConstraintProductionLimitedCohortPolicyV1,
    PromptConstraintProductionLimitedDecisionV1,
    PromptConstraintProductionLimitedMonitoringPlanV1,
    PromptConstraintProductionLimitedOperatorChecklistV1,
    PromptConstraintProductionLimitedPreflightGateV1,
    PromptConstraintProductionLimitedRollbackPlanV1,
    PromptConstraintProductionLimitedRolloutPlanV1,
)


PRD = "PRD-046.1.12"
SOURCE_PRD = "PRD-046.1.11"


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_source_artifacts(source_dir: Path) -> dict[str, Path]:
    return {
        "manifest": source_dir / "supervised_consolidation_manifest.json",
        "aggregate": source_dir / "supervised_consolidation_aggregate_metrics.json",
        "reproducibility": source_dir / "supervised_consolidation_reproducibility.json",
        "risk_register": source_dir / "supervised_consolidation_risk_register.json",
        "decision_gate": source_dir / "supervised_consolidation_rollout_decision_gate.json",
        "no_mutation": source_dir / "no_mutation_proof.json",
        "encoding_hygiene": source_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight(source_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
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


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {
        "all_blocks": repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": repo_root / "Bot_data_base" / "data" / "registry.json",
        "config": repo_root / "Bot_data_base" / "config.yaml",
    }
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "prompt_constraint_production_limited_rollout_plan_no_mutation_proof_v1",
        "prd": PRD,
        "tracked_paths": {
            "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
            "registry": "Bot_data_base/data/registry.json",
            "config": "Bot_data_base/config.yaml",
        },
        "all_blocks_merged_mutated": hash_before["all_blocks"] != hash_after["all_blocks"],
        "registry_mutated": hash_before["registry"] != hash_after["registry"],
        "config_mutated": hash_before["config"] != hash_after["config"],
        "chroma_reindex_performed": False,
        "production_apply_performed": False,
        "provider_called_by_plan": False,
        "execution_performed": False,
    }


def _operator_checklist_items() -> list[dict[str, Any]]:
    return [
        {"id": "confirm_scope", "required": True, "description": "Confirm this is production-limited execution, not broad rollout."},
        {"id": "confirm_allowlist", "required": True, "description": "Confirm only explicitly allowlisted user IDs are included."},
        {"id": "confirm_force_disabled_start", "required": True, "description": "Confirm FORCE_DISABLED starts as true before any run."},
        {"id": "capture_baseline_no_mutation", "required": True, "description": "Capture hashes before execution."},
        {"id": "enable_for_limited_window_only", "required": True, "description": "Enable test_apply only for limited manual window."},
        {"id": "capture_trace_samples", "required": True, "description": "Capture sanitized trace samples."},
        {"id": "run_normal_user_control", "required": True, "description": "Verify normal user path remains unchanged."},
        {"id": "rollback_force_disabled", "required": True, "description": "Set FORCE_DISABLED=true and verify no stale apply."},
        {"id": "compare_quality", "required": True, "description": "Compare baseline vs production-limited test_apply."},
        {"id": "final_decision", "required": True, "description": "Choose continue_limited/stay_limited/hotfix/stop after gate."},
    ]


def _operator_runbook(checklist: list[dict[str, Any]]) -> str:
    lines = [
        "# PRD-046.1.12 Production-Limited Operator Runbook",
        "",
        "This runbook is plan-only. Do not execute rollout in PRD-046.1.12.",
        "",
        "## Steps",
    ]
    for idx, item in enumerate(checklist, start=1):
        lines.append(f"{idx}. `{item['id']}` - {item['description']}")
    lines.extend(
        [
            "",
            "## Hard Rules",
            "- Keep `PROMPT_CONSTRAINT_PILOT_ENABLED=false` as baseline default.",
            "- Keep `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true` as baseline default.",
            "- No provider calls for planning stage.",
            "- No mutation of KB/registry/config/chroma.",
            "- Use sanitized traces only.",
        ]
    )
    return "\n".join(lines) + "\n"


def execute_rollout_plan(*, strict: bool, parsed: dict[str, Any]) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
]:
    manifest = _safe_dict(parsed.get("manifest"))
    aggregate = _safe_dict(parsed.get("aggregate"))
    reproducibility = _safe_dict(parsed.get("reproducibility"))
    risk_register = _safe_dict(parsed.get("risk_register"))
    decision_gate = _safe_dict(parsed.get("decision_gate"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation"))
    source_hygiene = _safe_dict(parsed.get("encoding_hygiene"))

    blockers: list[str] = []
    warnings: list[str] = []

    source_final_status = str(decision_gate.get("final_status", "blocked"))
    source_decision = str(decision_gate.get("decision", "blocked"))
    source_consolidation_passed = source_final_status == "passed"
    source_decision_ok = source_decision == "prepare_production_limited_rollout_plan"
    reproducibility_passed = _as_bool(reproducibility.get("reproducibility_passed"), False)
    risk_register_has_blockers = _as_bool(risk_register.get("risk_register_has_blockers"), True)
    provider_called_total = _as_int(aggregate.get("provider_called_total"), 1)
    source_production_mutation = _as_bool(aggregate.get("production_mutation_detected_any"), True)
    source_hygiene_passed = str(source_hygiene.get("final_status", "failed")) == "passed"

    if not source_consolidation_passed:
        blockers.append("source_consolidation_not_passed")
    if not source_decision_ok:
        blockers.append("source_decision_not_prepare_production_limited_rollout_plan")
    if not reproducibility_passed:
        blockers.append("source_reproducibility_not_passed")
    if risk_register_has_blockers:
        blockers.append("source_risk_register_has_blockers")
    if provider_called_total > 0:
        blockers.append("source_provider_called_total_gt_zero")
    if source_production_mutation:
        blockers.append("source_production_mutation_detected")
    if not source_hygiene_passed:
        blockers.append("source_artifact_hygiene_not_passed")

    source_no_mutation_green = not any(
        _as_bool(source_no_mutation.get(key), False)
        for key in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    if not source_no_mutation_green:
        blockers.append("source_no_mutation_not_green")

    cohort_policy = PromptConstraintProductionLimitedCohortPolicyV1(
        excluded_user_categories=[
            "crisis_or_self_harm_context",
            "minor_or_unknown_age_sensitive_context",
            "high_emotional_distress_without_safety_review",
            "users_not_explicitly_allowlisted",
            "users_without_operator_review",
        ]
    ).to_dict()

    preflight_gates = PromptConstraintProductionLimitedPreflightGateV1(
        required_before_execution={
            "source_consolidation_passed": True,
            "operator_checklist_completed": True,
            "rollback_plan_reviewed": True,
            "monitoring_plan_ready": True,
            "abort_criteria_ready": True,
            "normal_user_control_case_ready": True,
            "trace_sanitization_ready": True,
            "no_mutation_baseline_captured": True,
            "config_default_conservative": True,
            "force_disabled_rollback_available": True,
        },
        blocked_if=[
            "source_consolidation_missing",
            "rollback_plan_missing",
            "operator_checklist_missing",
            "abort_criteria_missing",
            "monitoring_plan_missing",
            "config_defaults_not_conservative",
            "force_disabled_priority_unclear",
        ],
    ).to_dict()

    checklist_items = _operator_checklist_items()
    operator_checklist = PromptConstraintProductionLimitedOperatorChecklistV1(checklist=checklist_items).to_dict()

    monitoring_plan = PromptConstraintProductionLimitedMonitoringPlanV1(
        metrics={
            "apply_count": "count test_apply activations",
            "normal_user_apply_count": "must remain 0",
            "rollback_failure_count": "must remain 0",
            "safety_regression_count": "must remain 0",
            "kb_policy_regression_count": "must remain 0",
            "prompt_bloat_regression_count": "must remain 0",
            "constraint_conflict_regression_count": "must remain 0",
            "raw_kb_text_exposure_count": "must remain 0",
            "internal_only_exposure_count": "must remain 0",
            "not_for_direct_quote_violation_count": "must remain 0",
            "provider_called_by_execution_count": "must remain 0 unless explicitly expected and separately approved",
            "production_mutation_detected": "must remain false",
        },
        trace_requirements={
            "sanitized_trace_only": True,
            "raw_prompt_forbidden": True,
            "raw_kb_text_forbidden": True,
            "private_user_text_forbidden": True,
        },
        observation_window={
            "manual_execution_only": True,
            "single_short_window": True,
            "automatic_background_monitoring_not_assumed": True,
        },
    ).to_dict()

    rollback_plan = PromptConstraintProductionLimitedRollbackPlanV1(
        rollback_priority="force_disabled_absolute_priority",
        primary_rollback={
            "set_PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
            "expected_apply_count_after_rollback": 0,
        },
        secondary_rollback={
            "set_PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "clear_allowlist": True,
        },
        verification={
            "run_allowlisted_control_after_rollback": True,
            "run_normal_user_control_after_rollback": True,
            "stale_apply_after_force_disabled_must_be": 0,
        },
        reporting={
            "rollback_proof_required": True,
            "rollback_failure_blocks_next_step": True,
        },
    ).to_dict()

    abort_criteria = PromptConstraintProductionLimitedAbortCriteriaV1(
        hard_abort_if=[
            "normal_user_apply_count > 0",
            "default_off_user_path_effect_count > 0",
            "allowlist_violation_count > 0",
            "rollback_failure_count > 0",
            "stale_apply_after_force_disabled_count > 0",
            "safety_regression_count > 0",
            "kb_policy_regression_count > 0",
            "prompt_bloat_regression_count > 0",
            "constraint_conflict_regression_count > 0",
            "raw_kb_text_exposure_count > 0",
            "internal_only_exposure_count > 0",
            "not_for_direct_quote_violation_count > 0",
            "production_mutation_detected=true",
            "config_mutated=true",
            "registry_mutated=true",
            "all_blocks_merged_mutated=true",
            "chroma_reindex_performed=true",
            "trace_sanitization_failed=true",
            "operator_checklist_incomplete=true",
        ],
        warning_if=[
            "apply_count lower than expected",
            "trace_samples_count lower than expected",
            "manual operator notes missing",
            "risk_register medium risks unresolved",
        ],
    ).to_dict()

    rollout_plan_ready = True
    cohort_policy_ready = (
        cohort_policy["max_initial_real_user_count"] <= 1
        and cohort_policy["max_total_users_in_first_execution_prd"] <= 2
        and cohort_policy["allowlist_required"] is True
        and cohort_policy["automatic_enrollment_allowed"] is False
    )
    preflight_gates_ready = len(preflight_gates.get("required_before_execution", {})) > 0
    operator_checklist_ready = len(operator_checklist.get("checklist", [])) >= 10
    monitoring_plan_ready = len(monitoring_plan.get("metrics", {})) > 0
    rollback_plan_ready = rollback_plan.get("rollback_priority") == "force_disabled_absolute_priority"
    abort_criteria_ready = len(abort_criteria.get("hard_abort_if", [])) > 0

    source_ok = (
        source_consolidation_passed
        and source_decision_ok
        and reproducibility_passed
        and not risk_register_has_blockers
        and provider_called_total == 0
        and not source_production_mutation
        and source_hygiene_passed
        and source_no_mutation_green
    )

    hard_blocked = strict and len(blockers) > 0
    if hard_blocked:
        final_status = "blocked"
        decision = "blocked"
        recommended_next_prd = "PRD-046.1.12-BLOCKER - Production-Limited Rollout Planning Blocker Resolution v1"
    elif source_ok and all(
        [
            rollout_plan_ready,
            cohort_policy_ready,
            preflight_gates_ready,
            operator_checklist_ready,
            monitoring_plan_ready,
            rollback_plan_ready,
            abort_criteria_ready,
        ]
    ):
        final_status = "passed"
        decision = "ready_for_production_limited_execution_prd"
        recommended_next_prd = "PRD-046.1.13 - Production-Limited Prompt-Constraint Pilot Execution / Monitoring Gate v1"
    elif source_ok:
        final_status = "passed"
        decision = "stay_supervised"
        recommended_next_prd = "PRD-046.1.12-HF1 - Production-Limited Plan Evidence Gap Fix v1"
        warnings.append("plan_sections_not_fully_ready")
    else:
        final_status = "needs_hotfix"
        decision = "hotfix_required"
        recommended_next_prd = "PRD-046.1.12-HF1 - Production-Limited Rollout Plan Hotfix v1"

    readiness_gate = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_consolidation_passed": source_consolidation_passed,
        "source_decision": source_decision,
        "rollout_plan_ready": rollout_plan_ready,
        "cohort_policy_ready": cohort_policy_ready,
        "preflight_gates_ready": preflight_gates_ready,
        "operator_checklist_ready": operator_checklist_ready,
        "monitoring_plan_ready": monitoring_plan_ready,
        "rollback_plan_ready": rollback_plan_ready,
        "abort_criteria_ready": abort_criteria_ready,
        "execution_performed": False,
        "provider_called_by_plan": False,
        "production_mutation_detected": False,
        "default_flags_changed": False,
        "recommended_next_prd": recommended_next_prd,
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = PromptConstraintProductionLimitedDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()

    rollout_plan = PromptConstraintProductionLimitedRolloutPlanV1(
        source_decision=source_decision,
        rollout_stage="plan_only",
        production_execution_performed=False,
        baseline_defaults={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
        },
        cohort_policy=cohort_policy,
        preflight_gates=preflight_gates,
        operator_checklist=operator_checklist,
        monitoring_plan=monitoring_plan,
        rollback_plan=rollback_plan,
        abort_criteria=abort_criteria,
        decision=decision,
    ).to_dict()

    rollout_plan["source_consolidation_final_status"] = source_final_status
    rollout_plan["source_consolidation_passed"] = source_consolidation_passed
    rollout_plan["reproducibility_passed"] = reproducibility_passed
    rollout_plan["risk_register_has_blockers"] = risk_register_has_blockers
    rollout_plan["provider_called_total"] = provider_called_total
    rollout_plan["production_mutation_detected_any"] = source_production_mutation
    rollout_plan["generated_at"] = _utc_now()

    runbook = _operator_runbook(checklist_items)

    return (
        rollout_plan,
        cohort_policy,
        preflight_gates,
        operator_checklist,
        monitoring_plan,
        rollback_plan,
        abort_criteria,
        readiness_gate,
        decision_payload,
        runbook,
    )
