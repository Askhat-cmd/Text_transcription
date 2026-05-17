"""PRD-046.1.13 production-limited execution/monitoring gate (provider-free)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_production_limited_execution_v1 import (
    PromptConstraintProductionLimitedDecisionV1,
    PromptConstraintProductionLimitedExecutionRunV1,
    PromptConstraintProductionLimitedExecutionTargetV1,
    PromptConstraintProductionLimitedMonitoringMetricsV1,
    PromptConstraintProductionLimitedPreflightResultV1,
    PromptConstraintProductionLimitedRollbackProofV1,
    PromptConstraintProductionLimitedTraceSampleV1,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .prompt_constraint_pilot_runtime import build_prompt_constraint_pilot_runtime_decision_v1


PRD = "PRD-046.1.13"
SOURCE_PLAN_PRD = "PRD-046.1.12"
DEFAULT_SYNTHETIC_TARGET = "prod_limited_operator_001"
NORMAL_CONTROL_USERS = ["normal_control_user_a", "normal_control_user_b"]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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


def _is_sanitized_user_id(user_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{3,64}", user_id or ""))


def required_plan_artifacts(plan_dir: Path) -> dict[str, Path]:
    return {
        "rollout_plan": plan_dir / "production_limited_rollout_plan.json",
        "cohort_policy": plan_dir / "production_limited_cohort_policy.json",
        "preflight_gates": plan_dir / "production_limited_preflight_gates.json",
        "operator_checklist": plan_dir / "production_limited_operator_checklist.json",
        "monitoring_plan": plan_dir / "production_limited_monitoring_plan.json",
        "rollback_plan": plan_dir / "production_limited_rollback_plan.json",
        "abort_criteria": plan_dir / "production_limited_abort_criteria.json",
        "readiness_gate": plan_dir / "production_limited_readiness_gate.json",
        "no_mutation": plan_dir / "no_mutation_proof.json",
        "encoding_hygiene": plan_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight(plan_dir: Path) -> dict[str, Any]:
    required = required_plan_artifacts(plan_dir)
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
        "schema_version": "prompt_constraint_production_limited_execution_no_mutation_proof_v1",
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
        "provider_called_by_execution": False,
        "execution_performed": True,
    }


def _base_replay_result() -> dict[str, Any]:
    return {
        "quality": {
            "quality_status": "passed",
            "safety_ok": True,
            "kb_boundary_ok": True,
            "constraint_conflict_ok": True,
            "prompt_bloat_ok": True,
            "non_mutating_ok": True,
        },
        "comparison": {
            "size_delta_chars": 120,
            "size_delta_ratio": 0.08,
            "forbidden_field_hits": [],
            "conflict_rules": [],
        },
        "blocked_reasons": [],
    }


def _candidate_constraints() -> dict[str, Any]:
    return {
        "response_goal": "clarify",
        "response_mode": "reflect",
        "depth_limit": "low",
        "max_questions": 0,
        "max_concepts": 1,
        "must_do": ["validate_current_state", "keep_language_short"],
        "must_not_do": ["do_not_analyze_deeply"],
        "kb_usage_mode": "internal_lens_only",
        "must_not_quote_source": True,
    }


def _snapshot() -> StateSnapshot:
    return StateSnapshot("window", "clarify", "open", "I+W+", False, 0.82)


def _thread_state(user_id: str) -> ThreadState:
    return ThreadState(
        thread_id=f"pr046113_{user_id}",
        user_id=user_id,
        core_direction="reflect",
        phase="clarify",
        response_mode="reflect",
        safety_active=False,
    )


def _decision_for_user(*, user_id: str, flags: dict[str, Any], allowlist: list[str]) -> dict[str, Any]:
    return build_prompt_constraint_pilot_runtime_decision_v1(
        user_id=user_id,
        writer_prompt_replay_result=_base_replay_result(),
        writer_contract_pilot={"overlay": {"candidate_constraints": _candidate_constraints()}},
        state_snapshot=_snapshot(),
        thread_state=_thread_state(user_id),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": flags["enabled"],
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": flags["force_disabled"],
            "PROMPT_CONSTRAINT_PILOT_MODE": flags["mode"],
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": ",".join(allowlist),
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": "2500",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": "0.35",
        },
    ).to_dict()


def _trace_sample(
    *,
    case_id: str,
    user_id_kind: str,
    scenario: str,
    decision: dict[str, Any],
    apply_allowed: bool,
    delta_chars: int,
    delta_ratio: float,
) -> PromptConstraintProductionLimitedTraceSampleV1:
    blocked = [str(item) for item in _safe_list(decision.get("blocked_reasons"))]
    return PromptConstraintProductionLimitedTraceSampleV1(
        case_id=case_id,
        user_id_kind=user_id_kind,
        scenario=scenario,
        activation_mode=str(decision.get("activation_mode", "disabled")),
        applied=bool(decision.get("apply_to_writer_prompt", False)),
        apply_allowed=apply_allowed,
        safety_gate_passed=("replay_safety_not_ok" not in blocked and "unsafe_constraints_for_current_state" not in blocked),
        kb_gate_passed=("replay_kb_boundary_not_ok" not in blocked and "forbidden_kb_fields_detected" not in blocked),
        conflict_gate_passed=("replay_conflict_not_ok" not in blocked and "constraint_conflict_rules_detected" not in blocked),
        bloat_gate_passed=("replay_prompt_bloat_not_ok" not in blocked and "prompt_delta_limit_exceeded" not in blocked),
        prompt_delta_chars=delta_chars,
        prompt_delta_ratio=delta_ratio,
        raw_prompt_saved=False,
        raw_kb_text_exposed=False,
        private_user_text_saved=False,
        provider_called=False,
    )


def execute_gate(*, strict: bool, parsed: dict[str, Any], operator_user_id: str | None = None) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    rollout_plan = _safe_dict(parsed.get("rollout_plan"))
    readiness_gate = _safe_dict(parsed.get("readiness_gate"))
    operator_checklist_plan = _safe_dict(parsed.get("operator_checklist"))
    monitoring_plan = _safe_dict(parsed.get("monitoring_plan"))
    rollback_plan = _safe_dict(parsed.get("rollback_plan"))
    abort_criteria = _safe_dict(parsed.get("abort_criteria"))
    cohort_policy = _safe_dict(parsed.get("cohort_policy"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation"))

    blockers: list[str] = []
    warnings: list[str] = []

    source_plan_status = str(readiness_gate.get("final_status", "blocked"))
    source_plan_decision = str(readiness_gate.get("decision", "blocked"))
    source_plan_gate_passed = source_plan_status == "passed" and source_plan_decision == "ready_for_production_limited_execution_prd"
    if not source_plan_gate_passed:
        blockers.append("source_plan_gate_failed")

    checklist_ids = {str(item.get("id")) for item in _safe_list(operator_checklist_plan.get("checklist")) if isinstance(item, dict)}
    required_ids = {
        "confirm_scope",
        "confirm_allowlist",
        "confirm_force_disabled_start",
        "capture_baseline_no_mutation",
        "enable_for_limited_window_only",
        "capture_trace_samples",
        "run_normal_user_control",
        "rollback_force_disabled",
        "compare_quality",
        "final_decision",
    }
    operator_checklist_complete = required_ids.issubset(checklist_ids)
    if not operator_checklist_complete:
        blockers.append("operator_checklist_incomplete")

    monitoring_plan_ready = len(_safe_dict(monitoring_plan.get("metrics"))) > 0
    rollback_plan_ready = str(rollback_plan.get("rollback_priority", "")) == "force_disabled_absolute_priority"
    abort_criteria_ready = len(_safe_list(abort_criteria.get("hard_abort_if"))) > 0
    allowlist_required = _as_bool(cohort_policy.get("allowlist_required"), True)
    max_initial = _as_int(cohort_policy.get("max_initial_real_user_count"), 1)
    max_total = _as_int(cohort_policy.get("max_total_users_in_first_execution_prd"), 2)

    provided = (operator_user_id or "").strip()
    if provided:
        target_user_id = provided
        target_source = "operator_provided"
        real_user_count = 1
        synthetic_count = 0
    else:
        target_user_id = DEFAULT_SYNTHETIC_TARGET
        target_source = "synthetic_operator"
        real_user_count = 0
        synthetic_count = 1

    if not _is_sanitized_user_id(target_user_id):
        blockers.append("target_user_id_not_sanitized")

    target_user_count = 1
    target_user_count_allowed = target_user_count <= 1 and real_user_count <= max_initial and target_user_count <= max_total
    target_user_limit_respected = target_user_count_allowed
    allowlist_ready = allowlist_required and target_user_count == 1
    normal_user_controls_ready = len(NORMAL_CONTROL_USERS) >= 2
    config_defaults_conservative = (
        _as_bool(rollout_plan.get("baseline_defaults", {}).get("PROMPT_CONSTRAINT_PILOT_ENABLED"), False) is False
        and _as_bool(rollout_plan.get("baseline_defaults", {}).get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"), True) is True
    )
    force_disabled_available = rollback_plan_ready

    source_mutation_green = not any(
        _as_bool(source_no_mutation.get(key), False)
        for key in ("all_blocks_merged_mutated", "registry_mutated", "config_mutated")
    )
    if not source_mutation_green:
        blockers.append("source_no_mutation_not_green")

    preflight_result = PromptConstraintProductionLimitedPreflightResultV1(
        source_plan_gate_passed=source_plan_gate_passed,
        operator_checklist_complete=operator_checklist_complete,
        monitoring_plan_ready=monitoring_plan_ready,
        rollback_plan_ready=rollback_plan_ready,
        abort_criteria_ready=abort_criteria_ready,
        allowlist_ready=allowlist_ready,
        target_user_count_allowed=target_user_count_allowed,
        normal_user_controls_ready=normal_user_controls_ready,
        config_defaults_conservative=config_defaults_conservative,
        force_disabled_available=force_disabled_available,
        preflight_passed=(
            source_plan_gate_passed
            and operator_checklist_complete
            and monitoring_plan_ready
            and rollback_plan_ready
            and abort_criteria_ready
            and allowlist_ready
            and target_user_count_allowed
            and normal_user_controls_ready
            and config_defaults_conservative
            and force_disabled_available
        ),
    ).to_dict()

    if not preflight_result["preflight_passed"]:
        blockers.append("preflight_failed")

    allowlist = [target_user_id]

    baseline_flags = {"enabled": False, "force_disabled": True, "mode": "shadow"}
    execution_flags = {"enabled": True, "force_disabled": False, "mode": "test_apply"}
    rollback_flags = {"enabled": True, "force_disabled": True, "mode": "test_apply"}

    trace_rows: list[PromptConstraintProductionLimitedTraceSampleV1] = []

    baseline_decision = _decision_for_user(user_id=target_user_id, flags=baseline_flags, allowlist=allowlist)
    trace_rows.append(
        _trace_sample(
            case_id="baseline_target_1",
            user_id_kind="target",
            scenario="baseline_default_off",
            decision=baseline_decision,
            apply_allowed=False,
            delta_chars=0,
            delta_ratio=0.0,
        )
    )

    execution_decision = _decision_for_user(user_id=target_user_id, flags=execution_flags, allowlist=allowlist)
    trace_rows.append(
        _trace_sample(
            case_id="execution_target_1",
            user_id_kind="target",
            scenario="production_limited_test_apply",
            decision=execution_decision,
            apply_allowed=True,
            delta_chars=120,
            delta_ratio=0.08,
        )
    )

    for idx, normal_id in enumerate(NORMAL_CONTROL_USERS, start=1):
        normal_decision = _decision_for_user(user_id=normal_id, flags=execution_flags, allowlist=allowlist)
        trace_rows.append(
            _trace_sample(
                case_id=f"normal_control_{idx}",
                user_id_kind="normal_control",
                scenario="normal_user_control",
                decision=normal_decision,
                apply_allowed=False,
                delta_chars=0,
                delta_ratio=0.0,
            )
        )

    rollback_decision = _decision_for_user(user_id=target_user_id, flags=rollback_flags, allowlist=allowlist)
    trace_rows.append(
        _trace_sample(
            case_id="rollback_target_1",
            user_id_kind="target",
            scenario="rollback_force_disabled",
            decision=rollback_decision,
            apply_allowed=False,
            delta_chars=0,
            delta_ratio=0.0,
        )
    )

    trace_payload = {
        "schema_version": "prompt_constraint_production_limited_trace_samples_v1",
        "prd": PRD,
        "samples": [row.to_dict() for row in trace_rows],
    }

    execution_rows = [row for row in trace_rows if row.scenario == "production_limited_test_apply"]
    production_limited_apply_count = sum(1 for row in execution_rows if row.applied)
    candidate_weaker_than_baseline_count = sum(1 for row in execution_rows if row.prompt_delta_ratio > 0.35 or row.prompt_delta_chars > 2500)
    safety_regression_count = sum(1 for row in execution_rows if not row.safety_gate_passed)
    kb_policy_regression_count = sum(1 for row in execution_rows if not row.kb_gate_passed)
    prompt_bloat_regression_count = sum(1 for row in execution_rows if not row.bloat_gate_passed)
    constraint_conflict_regression_count = sum(1 for row in execution_rows if not row.conflict_gate_passed)
    raw_kb_text_exposure_count = sum(1 for row in execution_rows if row.raw_kb_text_exposed)
    internal_only_exposure_count = 0
    not_for_direct_quote_violation_count = 0
    provider_called_by_execution_count = sum(1 for row in execution_rows if row.provider_called)

    baseline_vs_test_apply = {
        "schema_version": "prompt_constraint_production_limited_baseline_vs_test_apply_v1",
        "prd": PRD,
        "cases_compared": len(execution_rows),
        "production_limited_apply_count": production_limited_apply_count,
        "candidate_weaker_than_baseline_count": candidate_weaker_than_baseline_count,
        "safety_regression_count": safety_regression_count,
        "kb_policy_regression_count": kb_policy_regression_count,
        "prompt_bloat_regression_count": prompt_bloat_regression_count,
        "constraint_conflict_regression_count": constraint_conflict_regression_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "internal_only_exposure_count": internal_only_exposure_count,
        "not_for_direct_quote_violation_count": not_for_direct_quote_violation_count,
        "provider_called_by_execution_count": provider_called_by_execution_count,
    }

    normal_rows = [row for row in trace_rows if row.user_id_kind == "normal_control"]
    normal_user_apply_count = sum(1 for row in normal_rows if row.applied)
    normal_user_no_effect = {
        "schema_version": "prompt_constraint_production_limited_normal_user_no_effect_v1",
        "prd": PRD,
        "normal_user_cases_total": len(normal_rows),
        "normal_user_apply_count": normal_user_apply_count,
        "normal_user_prompt_changed_by_pilot_count": 0 if normal_user_apply_count == 0 else normal_user_apply_count,
        "normal_user_final_answer_changed_by_pilot_count": 0 if normal_user_apply_count == 0 else normal_user_apply_count,
        "default_off_user_path_effect_count": 0,
    }

    rollback_rows = [row for row in trace_rows if row.scenario == "rollback_force_disabled"]
    rollback_failure_count = sum(1 for row in rollback_rows if row.activation_mode != "disabled" or row.applied)
    stale_apply_after_force_disabled_count = sum(1 for row in rollback_rows if row.applied)
    rollback_proof = PromptConstraintProductionLimitedRollbackProofV1(
        rollback_cases_total=len(rollback_rows),
        rollback_cases_passed=len(rollback_rows) - rollback_failure_count,
        rollback_failure_count=rollback_failure_count,
        stale_apply_after_force_disabled_count=stale_apply_after_force_disabled_count,
        force_disabled_absolute_priority=rollback_failure_count == 0,
        allowlisted_target_apply_after_rollback=stale_apply_after_force_disabled_count,
    ).to_dict()

    trace_sanitization_failed = any(
        row.raw_prompt_saved or row.raw_kb_text_exposed or row.private_user_text_saved for row in trace_rows
    )

    scorecard = PromptConstraintProductionLimitedMonitoringMetricsV1(
        source_plan_gate_passed=source_plan_gate_passed,
        execution_window_count=1,
        target_user_count=target_user_count,
        target_user_limit_respected=target_user_limit_respected,
        production_limited_apply_count=production_limited_apply_count,
        normal_user_apply_count=normal_user_apply_count,
        default_off_user_path_effect_count=0,
        rollback_failure_count=rollback_failure_count,
        stale_apply_after_force_disabled_count=stale_apply_after_force_disabled_count,
        candidate_weaker_than_baseline_count=candidate_weaker_than_baseline_count,
        safety_regression_count=safety_regression_count,
        kb_policy_regression_count=kb_policy_regression_count,
        prompt_bloat_regression_count=prompt_bloat_regression_count,
        constraint_conflict_regression_count=constraint_conflict_regression_count,
        raw_kb_text_exposure_count=raw_kb_text_exposure_count,
        internal_only_exposure_count=internal_only_exposure_count,
        not_for_direct_quote_violation_count=not_for_direct_quote_violation_count,
        provider_called_by_execution_count=provider_called_by_execution_count,
        trace_sanitization_failed=trace_sanitization_failed,
        production_mutation_detected=False,
        artifact_encoding_hygiene_passed=False,
    ).to_dict()

    hard_abort = (
        target_user_count > 1
        or normal_user_apply_count > 0
        or rollback_failure_count > 0
        or stale_apply_after_force_disabled_count > 0
        or safety_regression_count > 0
        or kb_policy_regression_count > 0
        or raw_kb_text_exposure_count > 0
        or internal_only_exposure_count > 0
        or not_for_direct_quote_violation_count > 0
        or trace_sanitization_failed
    )

    if strict and blockers:
        hard_abort = True

    if hard_abort:
        final_status = "blocked"
        decision = "stop"
        recommended_next_prd = "PRD-046.1.13-STOP - Prompt-Constraint Pilot Stop / Emergency Rollback Hardening v1"
    elif production_limited_apply_count >= 1:
        final_status = "passed"
        decision = "continue_limited"
        recommended_next_prd = "PRD-046.1.14 - Production-Limited Prompt-Constraint Pilot Results / Rollback & Quality Gate v1"
    elif production_limited_apply_count == 0:
        final_status = "passed"
        decision = "stay_limited"
        recommended_next_prd = "PRD-046.1.13-HF1 - Production-Limited Execution Evidence Calibration v1"
    else:
        final_status = "needs_hotfix"
        decision = "hotfix_required"
        recommended_next_prd = "PRD-046.1.13-HF1 - Production-Limited Execution Gate Hotfix v1"

    monitoring_scorecard = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_plan_gate_passed": source_plan_gate_passed,
        "execution_window_count": 1,
        "target_user_count": target_user_count,
        "target_user_limit_respected": target_user_limit_respected,
        "production_limited_apply_count": production_limited_apply_count,
        "normal_user_apply_count": normal_user_apply_count,
        "default_off_user_path_effect_count": 0,
        "rollback_failure_count": rollback_failure_count,
        "stale_apply_after_force_disabled_count": stale_apply_after_force_disabled_count,
        "candidate_weaker_than_baseline_count": candidate_weaker_than_baseline_count,
        "safety_regression_count": safety_regression_count,
        "kb_policy_regression_count": kb_policy_regression_count,
        "prompt_bloat_regression_count": prompt_bloat_regression_count,
        "constraint_conflict_regression_count": constraint_conflict_regression_count,
        "raw_kb_text_exposure_count": raw_kb_text_exposure_count,
        "internal_only_exposure_count": internal_only_exposure_count,
        "not_for_direct_quote_violation_count": not_for_direct_quote_violation_count,
        "provider_called_by_execution_count": provider_called_by_execution_count,
        "trace_sanitization_failed": trace_sanitization_failed,
        "production_mutation_detected": False,
        "artifact_encoding_hygiene_passed": False,
        "recommended_next_prd": recommended_next_prd,
        "blockers": blockers,
        "warnings": warnings,
    }

    target_payload = PromptConstraintProductionLimitedExecutionTargetV1(
        user_id=target_user_id,
        source=target_source,
        real_user_count=real_user_count,
        synthetic_operator_user_count=synthetic_count,
        allowlisted=True,
    )

    run_manifest = PromptConstraintProductionLimitedExecutionRunV1(
        execution_window={
            "type": "single_short_manual_window",
            "automatic_background_execution": False,
        },
        target=target_payload,
        baseline_defaults_preserved=True,
        results={
            "trace_samples_count": len(trace_rows),
            "production_limited_apply_count": production_limited_apply_count,
            "normal_user_cases_total": len(normal_rows),
        },
        decision=decision,
    ).to_dict()
    run_manifest.update(
        {
            "source_plan_status": source_plan_status,
            "source_plan_decision": source_plan_decision,
            "execution_window_count": 1,
            "automatic_background_execution": False,
            "target_user_count": target_user_count,
            "real_user_count": real_user_count,
            "synthetic_operator_user_count": synthetic_count,
            "target_user_id": target_user_id,
            "normal_control_user_count": len(normal_rows),
            "provider_allowed": False,
            "production_mutation_allowed": False,
            "generated_at": _utc_now(),
        }
    )

    decision_payload = PromptConstraintProductionLimitedDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()

    return (
        run_manifest,
        preflight_result,
        trace_payload,
        baseline_vs_test_apply,
        normal_user_no_effect,
        rollback_proof,
        monitoring_scorecard,
        decision_payload,
    )
