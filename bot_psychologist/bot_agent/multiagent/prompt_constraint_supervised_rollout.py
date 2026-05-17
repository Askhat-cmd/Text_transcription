"""PRD-046.1.8 supervised prompt-constraint rollout plan builder."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..feature_flags import _DEFAULTS as BOOL_DEFAULTS
from ..feature_flags import _STRING_DEFAULTS as STRING_DEFAULTS
from .contracts.prompt_constraint_supervised_rollout_v1 import (
    PromptConstraintRolloutAbortCriteriaV1,
    PromptConstraintRolloutCohortV1,
    PromptConstraintRolloutDecisionV1,
    PromptConstraintRolloutGateV1,
    PromptConstraintRolloutMetricV1,
    PromptConstraintSupervisedRolloutPlanV1,
)


PRD = "PRD-046.1.8"
SOURCE_PRD = "PRD-046.1.7"


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_source_artifacts(input_dir: Path) -> dict[str, Path]:
    return {
        "runtime_evidence_audit": input_dir / "runtime_evidence_audit.json",
        "rollback_toggle_matrix": input_dir / "rollback_toggle_matrix.json",
        "quality_delta": input_dir / "baseline_vs_test_apply_quality_delta.json",
        "gate_verification": input_dir / "prompt_constraint_pilot_gate_verification.json",
        "quality_gate_scorecard": input_dir / "prompt_constraint_pilot_quality_gate_scorecard.json",
        "no_mutation": input_dir / "no_mutation_proof.json",
        "encoding_hygiene": input_dir / "artifact_encoding_hygiene_report.json",
        "report_impl": Path("TO_DO_LIST/reports/PRD-046.1.7_IMPLEMENTATION_REPORT.md"),
        "report_gate": Path("TO_DO_LIST/reports/PRD-046.1.7_PROMPT_CONSTRAINT_PILOT_QUALITY_GATE_REPORT.md"),
        "project_state": Path("docs/PROJECT_STATE.md"),
        "roadmap": Path("docs/ROADMAP.md"),
        "prd_index": Path("docs/PRD_INDEX.md"),
    }


def preflight(input_dir: Path, repo_root: Path) -> dict[str, Any]:
    required = required_source_artifacts(input_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, rel in required.items():
        path = rel if rel.is_absolute() else (repo_root / rel)
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
            try:
                parsed[key] = _read_json(path)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {key: str((value if value.is_absolute() else (repo_root / value)).resolve()) for key, value in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def hard_abort_conditions() -> list[str]:
    return [
        "normal_user_apply_count > 0",
        "allowlist_violation_count > 0",
        "default_off_user_path_effect_count > 0",
        "rollback_failure_count > 0",
        "stale_apply_after_force_disabled_count > 0",
        "raw_kb_text_exposure_count > 0",
        "internal_only_exposure_count > 0",
        "not_for_direct_quote_violation_count > 0",
        "safety_regression_count > 0",
        "kb_policy_regression_count > 0",
        "candidate_weaker_than_baseline_count > 0",
        "prompt_bloat_regression_count > 0",
        "constraint_conflict_regression_count > 0",
        "provider_called_by_gate_count > 0",
        "production_mutation_detected=true",
    ]


def warning_conditions() -> list[str]:
    return [
        "trace_samples_count < expected_minimum",
        "candidate_tighter_than_baseline_count lower than expected",
        "datetime.utcnow deprecation warnings remain",
        "operator_runbook_missing_optional_markdown",
    ]


def rollback_steps() -> list[str]:
    return [
        "Set PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true immediately.",
        "Set PROMPT_CONSTRAINT_PILOT_ENABLED=false immediately.",
        "Keep PROMPT_CONSTRAINT_PILOT_MODE=shadow for inspection-only traces.",
        "Collect trace artifacts and verify normal_user_apply_count=0.",
        "Re-run supervised rollout gates before any re-enable request.",
    ]


def build_toggle_matrix() -> dict[str, Any]:
    cases = [
        ("false_true_shadow_normal", False, True, "shadow", "normal_user", "disabled/no_apply"),
        ("true_true_test_apply_allowlisted", True, True, "test_apply", "pilot_user", "disabled/no_apply"),
        ("true_false_shadow_allowlisted", True, False, "shadow", "pilot_user", "shadow_only/no_apply"),
        ("true_false_test_apply_normal", True, False, "test_apply", "normal_user", "shadow_only/no_apply"),
        ("true_false_test_apply_non_allowlisted", True, False, "test_apply", "external_user", "shadow_only/no_apply"),
        ("true_false_test_apply_pilot_prefix", True, False, "test_apply", "pilot_demo", "apply_if_all_gates_pass"),
        ("true_false_test_apply_explicit_allowlist", True, False, "test_apply", "pilot_user", "apply_if_all_gates_pass"),
        ("true_false_test_apply_allowlisted_safety_fail", True, False, "test_apply", "pilot_user", "downgrade_or_block"),
        ("true_false_test_apply_allowlisted_kb_fail", True, False, "test_apply", "pilot_user", "downgrade_or_block"),
        ("true_false_test_apply_allowlisted_bloat_conflict_fail", True, False, "test_apply", "pilot_user", "downgrade_or_block"),
    ]
    rows: list[dict[str, Any]] = []
    for case_id, enabled, force_disabled, mode, user, expected in cases:
        rows.append(
            {
                "case_id": case_id,
                "enabled": enabled,
                "force_disabled": force_disabled,
                "mode": mode,
                "user": user,
                "expected": expected,
            }
        )
    return {
        "schema_version": "prompt_constraint_supervised_rollout_toggle_matrix_v1",
        "prd": PRD,
        "toggle_matrix_ready": True,
        "rows": rows,
    }


def build_plan(*, parsed: dict[str, Any], strict: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_scorecard = _safe_dict(parsed.get("quality_gate_scorecard"))
    source_evidence = _safe_dict(parsed.get("runtime_evidence_audit"))
    source_rollback = _safe_dict(parsed.get("rollback_toggle_matrix"))
    source_quality = _safe_dict(parsed.get("quality_delta"))
    source_gate = _safe_dict(parsed.get("gate_verification"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation"))

    blockers: list[str] = []
    warnings: list[str] = []

    source_status_ok = str(source_scorecard.get("final_status", "")) == "passed"
    source_decision_ok = str(source_scorecard.get("decision", "")) == "supervised_rollout_candidate"
    if not source_status_ok:
        blockers.append("source_prd_046_1_7_final_status_not_passed")
    if not source_decision_ok:
        blockers.append("source_prd_046_1_7_decision_not_supervised_rollout_candidate")

    enabled_default_false = BOOL_DEFAULTS.get("PROMPT_CONSTRAINT_PILOT_ENABLED", True) is False
    force_disabled_default_true = BOOL_DEFAULTS.get("PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED", False) is True
    mode_default = str(STRING_DEFAULTS.get("PROMPT_CONSTRAINT_PILOT_MODE", "shadow"))
    conservative_mode_default = mode_default in {"shadow", "test_apply"}
    if not enabled_default_false:
        blockers.append("default_enabled_flag_is_not_false")
    if not force_disabled_default_true:
        blockers.append("default_force_disabled_flag_is_not_true")
    if not conservative_mode_default:
        blockers.append("default_mode_is_not_conservative")

    normal_user_apply = _as_int(source_scorecard.get("normal_user_apply_count"), 0)
    default_off_effect = _as_int(source_scorecard.get("default_off_user_path_effect_count"), 0)
    allowlist_viol = _as_int(source_scorecard.get("allowlist_violation_count"), 0)
    raw_kb = _as_int(source_scorecard.get("raw_kb_text_exposure_count"), 0)
    rollback_failure = _as_int(source_rollback.get("rollback_failure_count"), 0)
    stale_apply = _as_int(source_rollback.get("stale_apply_after_force_disabled_count"), 0)
    weaker = _as_int(source_quality.get("candidate_weaker_than_baseline_count"), 0)
    safety_reg = _as_int(source_quality.get("safety_regression_count"), 0)
    kb_reg = _as_int(source_quality.get("kb_policy_regression_count"), 0)
    bloat_reg = _as_int(source_quality.get("prompt_bloat_regression_count"), 0)
    conflict_reg = _as_int(source_quality.get("constraint_conflict_regression_count"), 0)
    provider_called = _as_int(source_gate.get("provider_called_by_gate_count"), 0)

    if normal_user_apply > 0:
        blockers.append("normal_user_apply_count_gt_zero")
    if default_off_effect > 0:
        blockers.append("default_off_user_path_effect_count_gt_zero")
    if allowlist_viol > 0:
        blockers.append("allowlist_violation_count_gt_zero")
    if raw_kb > 0:
        blockers.append("raw_kb_text_exposure_count_gt_zero")
    if rollback_failure > 0 or stale_apply > 0:
        blockers.append("rollback_failures_detected")
    if safety_reg > 0 or kb_reg > 0 or weaker > 0 or bloat_reg > 0 or conflict_reg > 0:
        blockers.append("quality_regression_detected")
    if provider_called > 0:
        blockers.append("provider_called_by_gate_count_gt_zero")

    production_mutation_detected = any(
        bool(source_no_mutation.get(name, False))
        for name in (
            "all_blocks_merged_mutated",
            "registry_mutated",
            "config_mutated",
            "chroma_reindex_performed",
            "production_apply_performed",
        )
    )
    if production_mutation_detected:
        blockers.append("production_mutation_detected")

    trace_samples = _as_int(source_evidence.get("trace_samples_count"), 0)
    tighter_count = _as_int(source_quality.get("candidate_tighter_than_baseline_count"), 0)
    if trace_samples < 10:
        warnings.append("trace_samples_count_below_expected_minimum")
    if tighter_count < 5:
        warnings.append("candidate_tighter_than_baseline_count_below_expected")
    warnings.append("datetime_utcnow_deprecation_warnings_possible")

    abort = PromptConstraintRolloutAbortCriteriaV1(
        hard_abort_conditions=hard_abort_conditions(),
        warning_conditions=warning_conditions(),
        rollback_steps=rollback_steps(),
        ready=True,
    )
    cohort = PromptConstraintRolloutCohortV1(
        allowlisted_user_ids_only=True,
        test_user_prefix_only=True,
        max_cohort_size=3,
        normal_users_allowed=False,
        explicit_allowlisted_user_ids=["pilot_user"],
        required_test_user_prefix="pilot_",
    )
    gates = [
        PromptConstraintRolloutGateV1(
            gate_id="source_prd_046_1_7_passed",
            required=True,
            passed=source_status_ok and source_decision_ok,
            details="Requires PRD-046.1.7 final_status=passed and decision=supervised_rollout_candidate.",
        ),
        PromptConstraintRolloutGateV1(
            gate_id="default_flags_conservative",
            required=True,
            passed=enabled_default_false and force_disabled_default_true and conservative_mode_default,
            details="Default values must remain enabled=false, force_disabled=true, mode in shadow/test_apply.",
        ),
        PromptConstraintRolloutGateV1(
            gate_id="rollback_first_preserved",
            required=True,
            passed=rollback_failure == 0 and stale_apply == 0,
            details="Rollback failure and stale apply counts must remain zero.",
        ),
        PromptConstraintRolloutGateV1(
            gate_id="normal_user_no_effect",
            required=True,
            passed=normal_user_apply == 0 and default_off_effect == 0,
            details="No apply and no default-off side effect on normal users.",
        ),
    ]
    metrics = [
        PromptConstraintRolloutMetricV1(
            metric_id="normal_user_apply_count",
            source="PRD-046.1.7 scorecard/gate verification",
            target="0",
            required=True,
        ),
        PromptConstraintRolloutMetricV1(
            metric_id="rollback_failure_count",
            source="PRD-046.1.7 rollback matrix",
            target="0",
            required=True,
        ),
        PromptConstraintRolloutMetricV1(
            metric_id="safety_kb_regression_counts",
            source="PRD-046.1.7 quality delta",
            target="all zero",
            required=True,
        ),
        PromptConstraintRolloutMetricV1(
            metric_id="trace_samples_count",
            source="PRD-046.1.7 runtime evidence audit",
            target=">=10",
            required=True,
        ),
    ]

    plan = PromptConstraintSupervisedRolloutPlanV1(
        baseline_defaults={
            "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
            "PROMPT_CONSTRAINT_PILOT_MODE": "shadow|test_apply",
        },
        rollout_stage="plan_only",
        allowed_scope=cohort,
        required_preflight_gates=gates,
        runtime_observation_requirements=metrics,
        abort_criteria=abort,
        rollback_steps=rollback_steps(),
        success_criteria=[
            "All required rollout gates passed.",
            "Normal user path remains unchanged.",
            "Rollback-first policy preserved.",
            "No production mutation and no provider-dependent acceptance.",
        ],
    )

    if blockers:
        final_status = "blocked" if strict else "needs_hotfix"
        decision = "execution_blocked" if strict else "hotfix_required"
        recommended = "PRD-046.1.8-HF1 - Supervised Rollout Plan Gate Fix"
    else:
        final_status = "passed"
        decision = "ready_for_supervised_execution_prd"
        recommended = "PRD-046.1.9 - Supervised Prompt-Constraint Pilot Execution / Observability Gate v1"

    readiness = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_gate": {
            "prd_046_1_7_final_status": str(source_scorecard.get("final_status", "")),
            "prd_046_1_7_decision": str(source_scorecard.get("decision", "")),
        },
        "default_safety": {
            "enabled_default_false": enabled_default_false,
            "force_disabled_default_true": force_disabled_default_true,
            "normal_user_apply_count": normal_user_apply,
            "default_off_user_path_effect_count": default_off_effect,
        },
        "rollback": {
            "rollback_first_policy_preserved": rollback_failure == 0 and stale_apply == 0,
            "force_disabled_absolute_priority": rollback_failure == 0 and stale_apply == 0,
            "toggle_matrix_ready": True,
        },
        "scope": {
            "normal_users_allowed": False,
            "allowlist_required": True,
            "test_prefix_required": True,
            "max_initial_cohort_size": 3,
        },
        "quality": {
            "requires_baseline_vs_test_apply_comparison": True,
            "requires_trace_samples": True,
            "requires_no_safety_regression": True,
            "requires_no_kb_policy_regression": True,
        },
        "mutation": {
            "production_apply_performed": False,
            "config_mutated": False,
            "registry_mutated": False,
            "all_blocks_merged_mutated": False,
            "chroma_reindex_performed": False,
        },
        "blockers": blockers,
        "warnings": warnings,
    }

    abort_payload = abort.to_dict()
    abort_payload["prd"] = PRD
    abort_payload["generated_at"] = _utc_now()

    toggle = build_toggle_matrix()
    toggle["generated_at"] = _utc_now()

    runbook = {
        "schema_version": "prompt_constraint_supervised_rollout_operator_runbook_v1",
        "prd": PRD,
        "runbook_stage": "plan_only_no_execution",
        "steps": [
            "Run preflight and verify PRD-046.1.7 final_status=passed and decision=supervised_rollout_candidate.",
            "Keep defaults conservative: enabled=false and force_disabled=true before any supervised request.",
            "For supervised execution PRD, manually set flags only for the approved session cohort.",
            "Keep initial cohort size <= 3 and allowlisted/test-prefix only.",
            "Capture trace artifacts after each supervised run and verify normal_user_apply_count=0.",
            "Verify rollback matrix by toggling force_disabled=true and confirming no stale apply.",
            "Disable pilot immediately by setting force_disabled=true and enabled=false if any abort condition is hit.",
            "Store rollout artifacts: scorecard, gate verification, quality delta, no-mutation proof, encoding report.",
            "Compare baseline vs test_apply metrics for every supervised cycle before continuation.",
            "Block next supervised step automatically if any hard abort condition is triggered.",
        ],
        "required_flags_for_future_execution": [
            "PROMPT_CONSTRAINT_PILOT_ENABLED",
            "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED",
            "PROMPT_CONSTRAINT_PILOT_MODE",
            "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS",
            "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX",
        ],
        "rollback_off_steps": rollback_steps(),
        "ready": True,
    }

    decision_payload = PromptConstraintRolloutDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended,
    ).to_dict()

    plan_payload = plan.to_dict()
    plan_payload["generated_at"] = _utc_now()
    plan_payload["source_prd"] = SOURCE_PRD
    plan_payload["source_scorecard_snapshot"] = {
        "final_status": str(source_scorecard.get("final_status", "")),
        "decision": str(source_scorecard.get("decision", "")),
        "evidence_quality": str(source_scorecard.get("evidence_quality", "")),
    }

    return plan_payload, readiness, abort_payload, toggle, runbook, decision_payload


def build_no_mutation_proof(*, repo_root: Path, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "prompt_constraint_supervised_rollout_no_mutation_proof_v1",
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
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked_files = {
        "all_blocks": repo_root / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json",
        "registry": repo_root / "Bot_data_base" / "data" / "registry.json",
        "config": repo_root / "Bot_data_base" / "config.yaml",
    }
    hashes = {name: _sha256(path) for name, path in tracked_files.items()}
    return tracked_files, hashes
