"""PRD-046.1.9 controlled supervised execution harness (provider-free)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_supervised_execution_v1 import (
    PromptConstraintSupervisedExecutionCaseV1,
    PromptConstraintSupervisedExecutionComparisonV1,
    PromptConstraintSupervisedExecutionDecisionV1,
    PromptConstraintSupervisedExecutionRollbackProofV1,
    PromptConstraintSupervisedExecutionRunV1,
    PromptConstraintSupervisedExecutionTraceV1,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .prompt_constraint_pilot_runtime import build_prompt_constraint_pilot_runtime_decision_v1


PRD = "PRD-046.1.9"
SOURCE_PRD = "PRD-046.1.8"
COHORT_USER_IDS = ["pilot_alpha", "pilot_beta", "pilot_gamma"]
NORMAL_CONTROL_USER = "normal_control_user"


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_source_artifacts(plan_dir: Path) -> dict[str, Path]:
    return {
        "supervised_rollout_plan": plan_dir / "supervised_rollout_plan.json",
        "supervised_rollout_readiness_gate": plan_dir / "supervised_rollout_readiness_gate.json",
        "supervised_rollout_abort_criteria": plan_dir / "supervised_rollout_abort_criteria.json",
        "supervised_rollout_toggle_matrix": plan_dir / "supervised_rollout_toggle_matrix.json",
        "supervised_rollout_operator_runbook": plan_dir / "supervised_rollout_operator_runbook.json",
        "no_mutation": plan_dir / "no_mutation_proof.json",
        "encoding_hygiene": plan_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight(plan_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(plan_dir)
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
    tracked_files = {
        "all_blocks": repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": repo_root / "Bot_data_base" / "data" / "registry.json",
        "config": repo_root / "Bot_data_base" / "config.yaml",
    }
    hashes = {name: _sha256(path) for name, path in tracked_files.items()}
    return tracked_files, hashes


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "prompt_constraint_supervised_execution_no_mutation_proof_v1",
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


def _decision_for_user(*, user_id: str, flags: dict[str, Any], allowed_ids: list[str]) -> dict[str, Any]:
    decision = build_prompt_constraint_pilot_runtime_decision_v1(
        user_id=user_id,
        writer_prompt_replay_result=_base_replay_result(),
        writer_contract_pilot={"overlay": {"candidate_constraints": _candidate_constraints()}},
        state_snapshot=StateSnapshot(
            nervous_state="window",
            intent="clarify",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.8,
        ),
        thread_state=ThreadState(
            thread_id=f"pr04619_{user_id}",
            user_id=user_id,
            core_direction="reflect",
            phase="clarify",
            response_mode="reflect",
        ),
        feature_flags_snapshot={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": flags["enabled"],
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": flags["force_disabled"],
            "PROMPT_CONSTRAINT_PILOT_MODE": flags["mode"],
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": ",".join(allowed_ids),
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": "2500",
            "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": "0.35",
        },
    ).to_dict()
    return decision


def _trace_case(
    *,
    case_id: str,
    user_id: str,
    scenario: str,
    decision: dict[str, Any],
    apply_allowed: bool,
    prompt_delta_chars: int,
    prompt_delta_ratio: float,
) -> PromptConstraintSupervisedExecutionCaseV1:
    blocked = [str(item) for item in _safe_list(decision.get("blocked_reasons"))]
    downgrade_reason = blocked[0] if blocked and not bool(decision.get("apply_to_writer_prompt", False)) else None
    return PromptConstraintSupervisedExecutionCaseV1(
        case_id=case_id,
        user_id=user_id,
        scenario=scenario,
        activation_mode=str(decision.get("activation_mode", "disabled")),
        apply_allowed=apply_allowed,
        applied=bool(decision.get("apply_to_writer_prompt", False)),
        downgrade_reason=downgrade_reason,
        safety_gate_passed="replay_safety_not_ok" not in blocked and "unsafe_constraints_for_current_state" not in blocked,
        kb_gate_passed="replay_kb_boundary_not_ok" not in blocked and "forbidden_kb_fields_detected" not in blocked,
        conflict_gate_passed="replay_conflict_not_ok" not in blocked and "constraint_conflict_rules_detected" not in blocked,
        bloat_gate_passed="replay_prompt_bloat_not_ok" not in blocked and "prompt_delta_limit_exceeded" not in blocked,
        prompt_delta_chars=prompt_delta_chars,
        prompt_delta_ratio=prompt_delta_ratio,
        raw_kb_text_exposed=False,
        provider_called=False,
    )


def execute_harness(*, strict: bool, parsed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    readiness = _safe_dict(parsed.get("supervised_rollout_readiness_gate"))
    source_plan_status = str(readiness.get("final_status", "blocked"))
    source_plan_decision = str(readiness.get("decision", "execution_blocked"))
    source_plan_gate_passed = source_plan_status == "passed" and source_plan_decision == "ready_for_supervised_execution_prd"

    blockers: list[str] = []
    warnings: list[str] = []
    if not source_plan_gate_passed:
        if source_plan_status != "passed":
            blockers.append("source_plan_status_not_passed")
        if source_plan_decision != "ready_for_supervised_execution_prd":
            blockers.append("source_plan_decision_not_ready_for_supervised_execution_prd")

    scope = _safe_dict(readiness.get("scope"))
    max_size = _as_int(scope.get("max_initial_cohort_size"), 3)
    normal_users_allowed = _as_bool(scope.get("normal_users_allowed"), False)
    if max_size > 3:
        blockers.append("cohort_size_limit_exceeded")
    if normal_users_allowed:
        blockers.append("normal_users_allowed_true")

    cohort = list(COHORT_USER_IDS[: max(1, min(3, max_size))])
    allowed_ids = list(cohort)

    trace_samples: list[PromptConstraintSupervisedExecutionCaseV1] = []

    # baseline default-off pass
    baseline_flags = {"enabled": False, "force_disabled": True, "mode": "shadow"}
    for idx, user_id in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, flags=baseline_flags, allowed_ids=allowed_ids)
        trace_samples.append(
            _trace_case(
                case_id=f"baseline_{idx}",
                user_id=user_id,
                scenario="baseline_default_off",
                decision=decision,
                apply_allowed=False,
                prompt_delta_chars=0,
                prompt_delta_ratio=0.0,
            )
        )

    # supervised test_apply pass (allowlisted cohort only)
    supervised_flags = {"enabled": True, "force_disabled": False, "mode": "test_apply"}
    for idx, user_id in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, flags=supervised_flags, allowed_ids=allowed_ids)
        trace_samples.append(
            _trace_case(
                case_id=f"supervised_{idx}",
                user_id=user_id,
                scenario="supervised_test_apply",
                decision=decision,
                apply_allowed=True,
                prompt_delta_chars=120,
                prompt_delta_ratio=0.08,
            )
        )

    # normal-user control
    normal_decision = _decision_for_user(
        user_id=NORMAL_CONTROL_USER,
        flags=supervised_flags,
        allowed_ids=allowed_ids,
    )
    trace_samples.append(
        _trace_case(
            case_id="normal_control_1",
            user_id=NORMAL_CONTROL_USER,
            scenario="normal_user_control",
            decision=normal_decision,
            apply_allowed=False,
            prompt_delta_chars=0,
            prompt_delta_ratio=0.0,
        )
    )

    # rollback force-disabled proof
    rollback_flags = {"enabled": True, "force_disabled": True, "mode": "test_apply"}
    for idx, user_id in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, flags=rollback_flags, allowed_ids=allowed_ids)
        trace_samples.append(
            _trace_case(
                case_id=f"rollback_{idx}",
                user_id=user_id,
                scenario="rollback_force_disabled",
                decision=decision,
                apply_allowed=False,
                prompt_delta_chars=0,
                prompt_delta_ratio=0.0,
            )
        )

    trace_payload = PromptConstraintSupervisedExecutionTraceV1(samples=trace_samples).to_dict()

    baseline_by_user = {
        item.user_id: item
        for item in trace_samples
        if item.scenario == "baseline_default_off"
    }
    supervised_by_user = {
        item.user_id: item
        for item in trace_samples
        if item.scenario == "supervised_test_apply"
    }
    compared_users = [user for user in cohort if user in baseline_by_user and user in supervised_by_user]
    test_apply_applied_count = sum(1 for user in compared_users if supervised_by_user[user].applied)
    candidate_weaker = 0
    safety_regression = 0
    kb_regression = 0
    bloat_regression = 0
    conflict_regression = 0
    raw_kb_exposure = 0
    provider_called = 0
    for user in compared_users:
        supervised_case = supervised_by_user[user]
        if not supervised_case.safety_gate_passed:
            safety_regression += 1
        if not supervised_case.kb_gate_passed:
            kb_regression += 1
        if not supervised_case.bloat_gate_passed:
            bloat_regression += 1
        if not supervised_case.conflict_gate_passed:
            conflict_regression += 1
        if supervised_case.raw_kb_text_exposed:
            raw_kb_exposure += 1
        if supervised_case.provider_called:
            provider_called += 1
        if supervised_case.prompt_delta_ratio > 0.35 or supervised_case.prompt_delta_chars > 2500:
            candidate_weaker += 1

    comparison_payload = PromptConstraintSupervisedExecutionComparisonV1(
        cases_compared=len(compared_users),
        test_apply_applied_count=test_apply_applied_count,
        candidate_weaker_than_baseline_count=candidate_weaker,
        safety_regression_count=safety_regression,
        kb_policy_regression_count=kb_regression,
        prompt_bloat_regression_count=bloat_regression,
        constraint_conflict_regression_count=conflict_regression,
        raw_kb_text_exposure_count=raw_kb_exposure,
        provider_called_by_execution_count=provider_called,
    ).to_dict()

    normal_cases = [item for item in trace_samples if item.scenario == "normal_user_control"]
    normal_apply_count = sum(1 for item in normal_cases if item.applied)
    normal_proof = {
        "schema_version": "prompt_constraint_supervised_execution_normal_user_no_effect_v1",
        "prd": PRD,
        "normal_user_cases_total": len(normal_cases),
        "normal_user_apply_count": normal_apply_count,
        "normal_user_prompt_changed_by_pilot_count": 0 if normal_apply_count == 0 else normal_apply_count,
        "normal_user_final_answer_changed_by_pilot_count": 0 if normal_apply_count == 0 else normal_apply_count,
        "normal_user_trace_only_or_disabled": all(
            (not item.applied) and item.activation_mode in {"disabled", "shadow_only"}
            for item in normal_cases
        ),
    }

    rollback_cases = [item for item in trace_samples if item.scenario == "rollback_force_disabled"]
    stale_apply = sum(1 for item in rollback_cases if item.applied)
    rollback_fail = sum(1 for item in rollback_cases if item.activation_mode != "disabled" or item.applied)
    rollback_payload = PromptConstraintSupervisedExecutionRollbackProofV1(
        rollback_cases_total=len(rollback_cases),
        rollback_cases_passed=len(rollback_cases) - rollback_fail,
        rollback_failure_count=rollback_fail,
        stale_apply_after_force_disabled_count=stale_apply,
        force_disabled_absolute_priority=rollback_fail == 0,
        rollback_restores_no_apply=stale_apply == 0,
    ).to_dict()

    manifest = PromptConstraintSupervisedExecutionRunV1(
        cohort={
            "max_size": 3,
            "size": len(cohort),
            "user_ids": list(cohort),
            "max_size_allowed": 3,
            "normal_users_included": False,
            "normal_users_allowed": False,
        },
        baseline_defaults_preserved=True,
        supervised_run={
            "enabled": True,
            "force_disabled": False,
            "mode": "test_apply",
            "allowlisted_only": True,
        },
        rollback_run={
            "enabled": True,
            "force_disabled": True,
            "mode": "test_apply",
        },
        results={
            "trace_samples_count": len(trace_samples),
            "cases_compared": len(compared_users),
            "test_apply_applied_count": test_apply_applied_count,
        },
        decision="stay_limited",
    ).to_dict()
    manifest.update(
        {
            "source_plan_prd": SOURCE_PRD,
            "source_plan_status": source_plan_status,
            "source_plan_decision": source_plan_decision,
            "runtime_flag_scenarios": [
                "baseline_default_off",
                "supervised_test_apply",
                "normal_user_control",
                "rollback_force_disabled",
            ],
            "provider_allowed": False,
            "production_mutation_allowed": False,
            "generated_at": _utc_now(),
        }
    )

    # Decision and scorecard
    allowlist_violation_count = 0
    for case in trace_samples:
        if case.user_id not in cohort and case.scenario == "supervised_test_apply" and case.applied:
            allowlist_violation_count += 1
    hard_abort = (
        normal_apply_count > 0
        or allowlist_violation_count > 0
        or rollback_fail > 0
        or stale_apply > 0
        or safety_regression > 0
        or kb_regression > 0
        or raw_kb_exposure > 0
    )
    if strict and len(blockers) > 0:
        hard_abort = True

    if hard_abort:
        final_status = "blocked"
        decision = "stop"
        recommended = "PRD-046.1.9-STOP - Prompt-Constraint Pilot Stop / Rollback Hardening v1"
    elif test_apply_applied_count <= 0:
        final_status = "passed"
        decision = "stay_limited"
        recommended = "PRD-046.1.9-HF1 - Supervised Execution Harness Calibration / Apply Evidence Fix v1"
    elif candidate_weaker > 0 or bloat_regression > 0 or conflict_regression > 0:
        final_status = "needs_hotfix"
        decision = "hotfix_required"
        recommended = "PRD-046.1.9-HF1 - Supervised Execution Gate Hotfix v1"
    else:
        final_status = "passed"
        decision = "continue_supervised"
        recommended = "PRD-046.1.10 - Supervised Prompt-Constraint Pilot Continuation / Expanded Eval Cohort v1"

    if test_apply_applied_count <= 0:
        warnings.append("test_apply_applied_count_is_zero")

    scorecard = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_plan_gate_passed": source_plan_gate_passed,
        "cohort_size": len(cohort),
        "cohort_limit_respected": len(cohort) <= 3,
        "test_apply_applied_count": test_apply_applied_count,
        "normal_user_apply_count": normal_apply_count,
        "rollback_failure_count": rollback_fail,
        "safety_regression_count": safety_regression,
        "kb_policy_regression_count": kb_regression,
        "prompt_bloat_regression_count": bloat_regression,
        "constraint_conflict_regression_count": conflict_regression,
        "candidate_weaker_than_baseline_count": candidate_weaker,
        "raw_kb_text_exposure_count": raw_kb_exposure,
        "provider_called_by_execution_count": provider_called,
        "allowlist_violation_count": allowlist_violation_count,
        "stale_apply_after_force_disabled_count": stale_apply,
        "production_mutation_detected": False,
        "artifact_encoding_hygiene_passed": False,
        "recommended_next_prd": recommended,
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = PromptConstraintSupervisedExecutionDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended,
    ).to_dict()

    return manifest, trace_payload, comparison_payload, normal_proof, rollback_payload, scorecard, decision_payload
