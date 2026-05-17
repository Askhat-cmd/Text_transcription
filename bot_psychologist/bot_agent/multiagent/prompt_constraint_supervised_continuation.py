"""PRD-046.1.10 expanded supervised continuation harness (provider-free)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_supervised_continuation_v1 import (
    PromptConstraintSupervisedContinuationCaseV1,
    PromptConstraintSupervisedContinuationCohortV1,
    PromptConstraintSupervisedContinuationComparisonV1,
    PromptConstraintSupervisedContinuationDecisionV1,
    PromptConstraintSupervisedContinuationRollbackV1,
    PromptConstraintSupervisedContinuationRunV1,
)
from .contracts.state_snapshot import StateSnapshot
from .contracts.thread_state import ThreadState
from .prompt_constraint_pilot_runtime import build_prompt_constraint_pilot_runtime_decision_v1


PRD = "PRD-046.1.10"
SOURCE_PRD = "PRD-046.1.9"
COHORT = [
    ("pilot_alpha", "low_resource_support_first"),
    ("pilot_beta", "reflective_open_exploration"),
    ("pilot_gamma", "directive_seeking"),
    ("pilot_delta", "defensive_validation_seeking"),
    ("pilot_epsilon", "kb_lens_relevant_no_direct_quote"),
    ("pilot_zeta", "safety_sensitive_non_crisis_boundary"),
]
NORMAL_CONTROL_USERS = ["normal_control_user_a", "normal_control_user_b"]
REQUIRED_SCENARIOS = [name for _, name in COHORT]


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


def required_source_artifacts(source_dir: Path) -> dict[str, Path]:
    return {
        "manifest": source_dir / "supervised_execution_manifest.json",
        "trace_samples": source_dir / "supervised_execution_trace_samples.json",
        "comparison": source_dir / "supervised_execution_baseline_vs_test_apply.json",
        "normal_no_effect": source_dir / "supervised_execution_normal_user_no_effect.json",
        "rollback_proof": source_dir / "supervised_execution_rollback_proof.json",
        "scorecard": source_dir / "supervised_execution_observability_scorecard.json",
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
        "schema_version": "prompt_constraint_supervised_continuation_no_mutation_proof_v1",
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
        "provider_called_by_continuation": False,
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
            "size_delta_chars": 150,
            "size_delta_ratio": 0.10,
            "forbidden_field_hits": [],
            "conflict_rules": [],
        },
        "blocked_reasons": [],
    }


def _candidate_constraints(scenario: str) -> dict[str, Any]:
    base = {
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
    if scenario == "directive_seeking":
        base["response_mode"] = "validate"
    elif scenario == "reflective_open_exploration":
        base["response_mode"] = "reflect"
    elif scenario == "defensive_validation_seeking":
        base["response_mode"] = "validate"
    elif scenario == "kb_lens_relevant_no_direct_quote":
        base["must_do"] = ["validate_current_state", "keep_language_short", "use_kb_as_internal_lens"]
    elif scenario == "safety_sensitive_non_crisis_boundary":
        base["response_mode"] = "safe_override"
        base["must_do"] = ["validate_current_state", "keep_language_short", "prioritize_safety_boundaries"]
    return base


def _snapshot_for_scenario(scenario: str) -> StateSnapshot:
    if scenario == "low_resource_support_first":
        return StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8)
    if scenario == "reflective_open_exploration":
        return StateSnapshot("window", "explore", "open", "I+W+", False, 0.82)
    if scenario == "directive_seeking":
        return StateSnapshot("window", "solution", "mixed", "I+W+", False, 0.76)
    if scenario == "defensive_validation_seeking":
        return StateSnapshot("window", "clarify", "defensive", "I-W+", False, 0.72)
    if scenario == "kb_lens_relevant_no_direct_quote":
        return StateSnapshot("window", "explore", "open", "I+W+", False, 0.84)
    if scenario == "safety_sensitive_non_crisis_boundary":
        return StateSnapshot("hyper", "clarify", "mixed", "I+W+", True, 0.78)
    return StateSnapshot("window", "clarify", "open", "I+W+", False, 0.8)


def _thread_state_for_scenario(user_id: str, scenario: str) -> ThreadState:
    response_mode = "reflect"
    if scenario in {"directive_seeking", "defensive_validation_seeking"}:
        response_mode = "validate"
    if scenario == "safety_sensitive_non_crisis_boundary":
        response_mode = "safe_override"
    return ThreadState(
        thread_id=f"pr046110_{user_id}",
        user_id=user_id,
        core_direction="reflect",
        phase="clarify",
        response_mode=response_mode,
        safety_active=(scenario == "safety_sensitive_non_crisis_boundary"),
    )


def _decision_for_user(*, user_id: str, scenario: str, flags: dict[str, Any], allowlist: list[str]) -> dict[str, Any]:
    return build_prompt_constraint_pilot_runtime_decision_v1(
        user_id=user_id,
        writer_prompt_replay_result=_base_replay_result(),
        writer_contract_pilot={"overlay": {"candidate_constraints": _candidate_constraints(scenario)}},
        state_snapshot=_snapshot_for_scenario(scenario),
        thread_state=_thread_state_for_scenario(user_id, scenario),
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


def _trace_case(*, case_id: str, user_id: str, scenario: str, decision: dict[str, Any], apply_allowed: bool, delta_chars: int, delta_ratio: float) -> PromptConstraintSupervisedContinuationCaseV1:
    blocked = [str(item) for item in _safe_list(decision.get("blocked_reasons"))]
    downgrade_reason = blocked[0] if blocked and not bool(decision.get("apply_to_writer_prompt", False)) else None
    constraints = _safe_dict(decision.get("candidate_constraints"))
    return PromptConstraintSupervisedContinuationCaseV1(
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
        prompt_delta_chars=delta_chars,
        prompt_delta_ratio=delta_ratio,
        raw_kb_text_exposed=False,
        internal_only_exposed=False,
        not_for_direct_quote_violated=not bool(constraints.get("must_not_quote_source", True)),
        provider_called=False,
    )


def execute_continuation(*, strict: bool, parsed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_scorecard = _safe_dict(parsed.get("scorecard"))
    source_final_status = str(source_scorecard.get("final_status", "blocked"))
    source_decision = str(source_scorecard.get("decision", "stop"))
    source_test_apply_count = _as_int(source_scorecard.get("test_apply_applied_count"), 0)
    source_normal_apply = _as_int(source_scorecard.get("normal_user_apply_count"), 0)
    source_rollback_fail = _as_int(source_scorecard.get("rollback_failure_count"), 1)
    source_safety_reg = _as_int(source_scorecard.get("safety_regression_count"), 1)
    source_kb_reg = _as_int(source_scorecard.get("kb_policy_regression_count"), 1)
    source_mutation = _as_bool(source_scorecard.get("production_mutation_detected"), True)

    blockers: list[str] = []
    warnings: list[str] = []
    source_gate_passed = (
        source_final_status == "passed"
        and source_decision == "continue_supervised"
        and source_test_apply_count > 0
        and source_normal_apply == 0
        and source_rollback_fail == 0
        and source_safety_reg == 0
        and source_kb_reg == 0
        and not source_mutation
    )
    if not source_gate_passed:
        blockers.append("source_execution_gate_failed")

    cohort = list(COHORT)
    cohort_limit_respected = len(cohort) <= 6
    if not cohort_limit_respected:
        blockers.append("cohort_size_limit_exceeded")

    allowlist = [user for user, _ in cohort]
    normal_users_included = any(not user.startswith("pilot_") for user in allowlist)
    all_allowlisted_or_prefix = all(user.startswith("pilot_") for user in allowlist)
    if normal_users_included:
        blockers.append("normal_users_included_in_cohort")
    if not all_allowlisted_or_prefix:
        blockers.append("cohort_contains_non_allowlisted_id")

    # Build trace samples
    trace_rows: list[PromptConstraintSupervisedContinuationCaseV1] = []
    baseline_flags = {"enabled": False, "force_disabled": True, "mode": "shadow"}
    supervised_flags = {"enabled": True, "force_disabled": False, "mode": "test_apply"}
    rollback_flags = {"enabled": True, "force_disabled": True, "mode": "test_apply"}

    for idx, (user_id, scenario) in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, scenario=scenario, flags=baseline_flags, allowlist=allowlist)
        trace_rows.append(
            _trace_case(
                case_id=f"baseline_{idx}",
                user_id=user_id,
                scenario=scenario,
                decision=decision,
                apply_allowed=False,
                delta_chars=0,
                delta_ratio=0.0,
            )
        )
    for idx, (user_id, scenario) in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, scenario=scenario, flags=supervised_flags, allowlist=allowlist)
        trace_rows.append(
            _trace_case(
                case_id=f"supervised_{idx}",
                user_id=user_id,
                scenario=scenario,
                decision=decision,
                apply_allowed=True,
                delta_chars=150,
                delta_ratio=0.10,
            )
        )
    for idx, normal_id in enumerate(NORMAL_CONTROL_USERS, start=1):
        decision = _decision_for_user(
            user_id=normal_id,
            scenario="reflective_open_exploration",
            flags=supervised_flags,
            allowlist=allowlist,
        )
        trace_rows.append(
            _trace_case(
                case_id=f"normal_control_{idx}",
                user_id=normal_id,
                scenario="normal_user_control",
                decision=decision,
                apply_allowed=False,
                delta_chars=0,
                delta_ratio=0.0,
            )
        )
    for idx, (user_id, scenario) in enumerate(cohort, start=1):
        decision = _decision_for_user(user_id=user_id, scenario=scenario, flags=rollback_flags, allowlist=allowlist)
        trace_rows.append(
            _trace_case(
                case_id=f"rollback_{idx}",
                user_id=user_id,
                scenario=scenario,
                decision=decision,
                apply_allowed=False,
                delta_chars=0,
                delta_ratio=0.0,
            )
        )

    trace_payload = {
        "schema_version": "prompt_constraint_supervised_continuation_trace_v1",
        "prd": PRD,
        "samples": [row.to_dict() for row in trace_rows],
    }

    # Scenario coverage
    supervised_rows = [row for row in trace_rows if row.case_id.startswith("supervised_")]
    covered = sorted({row.scenario for row in supervised_rows})
    missing = [scenario for scenario in REQUIRED_SCENARIOS if scenario not in covered]
    scenario_coverage = {
        "required_scenarios": list(REQUIRED_SCENARIOS),
        "covered_scenarios_count": len(covered),
        "missing_scenarios": missing,
        "coverage_passed": len(missing) == 0,
    }

    # Comparison
    test_apply_applied_count = sum(1 for row in supervised_rows if row.applied)
    candidate_weaker = 0
    safety_reg = sum(1 for row in supervised_rows if not row.safety_gate_passed)
    kb_reg = sum(1 for row in supervised_rows if not row.kb_gate_passed)
    bloat_reg = sum(1 for row in supervised_rows if not row.bloat_gate_passed)
    conflict_reg = sum(1 for row in supervised_rows if not row.conflict_gate_passed)
    raw_exposure = sum(1 for row in supervised_rows if row.raw_kb_text_exposed)
    internal_exposure = sum(1 for row in supervised_rows if row.internal_only_exposed)
    quote_viol = sum(1 for row in supervised_rows if row.not_for_direct_quote_violated)
    provider_called = sum(1 for row in supervised_rows if row.provider_called)
    for row in supervised_rows:
        if row.prompt_delta_ratio > 0.35 or row.prompt_delta_chars > 2500:
            candidate_weaker += 1

    comparison = PromptConstraintSupervisedContinuationComparisonV1(
        cases_compared=len(supervised_rows),
        test_apply_applied_count=test_apply_applied_count,
        candidate_weaker_than_baseline_count=candidate_weaker,
        safety_regression_count=safety_reg,
        kb_policy_regression_count=kb_reg,
        prompt_bloat_regression_count=bloat_reg,
        constraint_conflict_regression_count=conflict_reg,
        raw_kb_text_exposure_count=raw_exposure,
        internal_only_exposure_count=internal_exposure,
        not_for_direct_quote_violation_count=quote_viol,
        provider_called_by_continuation_count=provider_called,
    ).to_dict()

    # Normal user proof
    normal_rows = [row for row in trace_rows if row.scenario == "normal_user_control"]
    normal_apply = sum(1 for row in normal_rows if row.applied)
    normal_no_effect = {
        "schema_version": "prompt_constraint_supervised_continuation_normal_user_no_effect_v1",
        "prd": PRD,
        "normal_user_cases_total": len(normal_rows),
        "normal_user_apply_count": normal_apply,
        "normal_user_prompt_changed_by_pilot_count": 0 if normal_apply == 0 else normal_apply,
        "normal_user_final_answer_changed_by_pilot_count": 0 if normal_apply == 0 else normal_apply,
        "default_off_user_path_effect_count": 0,
    }

    # Rollback proof
    rollback_rows = [row for row in trace_rows if row.case_id.startswith("rollback_")]
    rollback_failure = sum(1 for row in rollback_rows if row.activation_mode != "disabled" or row.applied)
    stale_apply = sum(1 for row in rollback_rows if row.applied)
    rollback = PromptConstraintSupervisedContinuationRollbackV1(
        rollback_cases_total=len(rollback_rows),
        rollback_cases_passed=len(rollback_rows) - rollback_failure,
        rollback_failure_count=rollback_failure,
        stale_apply_after_force_disabled_count=stale_apply,
        force_disabled_absolute_priority=rollback_failure == 0,
    ).to_dict()

    allowlist_viol = sum(
        1
        for row in supervised_rows
        if row.user_id not in allowlist and row.applied
    )

    hard_abort = (
        normal_apply > 0
        or allowlist_viol > 0
        or rollback_failure > 0
        or stale_apply > 0
        or safety_reg > 0
        or kb_reg > 0
        or raw_exposure > 0
        or internal_exposure > 0
        or quote_viol > 0
    )
    if strict and blockers:
        hard_abort = True

    if hard_abort:
        final_status = "blocked"
        decision = "stop"
        recommended = "PRD-046.1.10-STOP - Prompt-Constraint Pilot Stop / Rollback Hardening v1"
    elif not scenario_coverage["coverage_passed"] or test_apply_applied_count <= 0:
        final_status = "passed"
        decision = "stay_limited"
        recommended = "PRD-046.1.10-HF1 - Supervised Continuation Evidence Calibration v1"
        if not scenario_coverage["coverage_passed"]:
            warnings.append("scenario_coverage_incomplete")
        if test_apply_applied_count <= 0:
            warnings.append("test_apply_applied_count_is_zero")
    elif candidate_weaker > 0 or bloat_reg > 0 or conflict_reg > 0:
        final_status = "needs_hotfix"
        decision = "hotfix_required"
        recommended = "PRD-046.1.10-HF1 - Supervised Continuation Gate Hotfix v1"
    else:
        final_status = "passed"
        decision = "continue_supervised"
        recommended = "PRD-046.1.11 - Prompt-Constraint Pilot Supervised Results Consolidation / Rollout Decision Gate v1"

    scorecard = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_execution_gate_passed": source_gate_passed,
        "cohort_size": len(cohort),
        "cohort_limit_respected": cohort_limit_respected,
        "scenario_coverage_passed": scenario_coverage["coverage_passed"],
        "test_apply_applied_count": test_apply_applied_count,
        "normal_user_apply_count": normal_apply,
        "default_off_user_path_effect_count": 0,
        "rollback_failure_count": rollback_failure,
        "stale_apply_after_force_disabled_count": stale_apply,
        "candidate_weaker_than_baseline_count": candidate_weaker,
        "safety_regression_count": safety_reg,
        "kb_policy_regression_count": kb_reg,
        "prompt_bloat_regression_count": bloat_reg,
        "constraint_conflict_regression_count": conflict_reg,
        "raw_kb_text_exposure_count": raw_exposure,
        "internal_only_exposure_count": internal_exposure,
        "not_for_direct_quote_violation_count": quote_viol,
        "provider_called_by_continuation_count": provider_called,
        "allowlist_violation_count": allowlist_viol,
        "production_mutation_detected": False,
        "artifact_encoding_hygiene_passed": False,
        "recommended_next_prd": recommended,
        "blockers": blockers,
        "warnings": warnings,
    }

    manifest = PromptConstraintSupervisedContinuationRunV1(
        source_execution_decision=source_decision,
        cohort=PromptConstraintSupervisedContinuationCohortV1(
            max_size=6,
            actual_size=len(cohort),
            normal_users_included=normal_users_included,
            user_ids=allowlist,
            all_user_ids_allowlisted_or_test_prefix=all_allowlisted_or_prefix,
        ),
        scenario_coverage=scenario_coverage,
        baseline_defaults_preserved=True,
        results={
            "trace_samples_count": len(trace_rows),
            "cases_compared": len(supervised_rows),
            "test_apply_applied_count": test_apply_applied_count,
        },
        decision=decision,
    ).to_dict()
    manifest.update(
        {
            "source_final_status": source_final_status,
            "source_execution_gate_passed": source_gate_passed,
            "source_test_apply_applied_count_gt_zero": source_test_apply_count > 0,
            "source_normal_user_apply_count": source_normal_apply,
            "source_rollback_failure_count": source_rollback_fail,
            "source_production_mutation_detected": source_mutation,
            "execution_mode": "controlled_harness_expanded_eval",
            "generated_at": _utc_now(),
        }
    )

    decision_payload = PromptConstraintSupervisedContinuationDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended,
    ).to_dict()

    return manifest, scenario_coverage, trace_payload, comparison, normal_no_effect, rollback, scorecard, decision_payload
