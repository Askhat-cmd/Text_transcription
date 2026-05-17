"""PRD-046.1.11 supervised consolidation gate (provider-free, evidence-only)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_supervised_consolidation_v1 import (
    PromptConstraintRolloutDecisionGateV1,
    PromptConstraintRolloutDecisionV1,
    PromptConstraintSupervisedAggregateMetricsV1,
    PromptConstraintSupervisedConsolidationRunV1,
    PromptConstraintSupervisedCycleEvidenceV1,
    PromptConstraintSupervisedRiskRegisterV1,
)


PRD = "PRD-046.1.11"
SOURCE_A_PRD = "PRD-046.1.9"
SOURCE_B_PRD = "PRD-046.1.10"


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


def required_source_artifacts(source_a_dir: Path, source_b_dir: Path) -> dict[str, Path]:
    return {
        "a_scorecard": source_a_dir / "supervised_execution_observability_scorecard.json",
        "a_comparison": source_a_dir / "supervised_execution_baseline_vs_test_apply.json",
        "a_normal_no_effect": source_a_dir / "supervised_execution_normal_user_no_effect.json",
        "a_rollback": source_a_dir / "supervised_execution_rollback_proof.json",
        "a_no_mutation": source_a_dir / "no_mutation_proof.json",
        "a_encoding_hygiene": source_a_dir / "artifact_encoding_hygiene_report.json",
        "b_scorecard": source_b_dir / "supervised_continuation_observability_scorecard.json",
        "b_scenario_coverage": source_b_dir / "supervised_continuation_scenario_coverage.json",
        "b_comparison": source_b_dir / "supervised_continuation_baseline_vs_test_apply.json",
        "b_normal_no_effect": source_b_dir / "supervised_continuation_normal_user_no_effect.json",
        "b_rollback": source_b_dir / "supervised_continuation_rollback_proof.json",
        "b_no_mutation": source_b_dir / "no_mutation_proof.json",
        "b_encoding_hygiene": source_b_dir / "artifact_encoding_hygiene_report.json",
    }


def preflight(source_a_dir: Path, source_b_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_a_dir, source_b_dir)
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
        "schema_version": "prompt_constraint_supervised_consolidation_no_mutation_proof_v1",
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
        "provider_called_by_consolidation": False,
    }


def _risk_register() -> list[dict[str, Any]]:
    return [
        {
            "risk_id": "limited_evidence_size",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Expand supervised evidence in rollout planning phase with strict abort criteria.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "synthetic_test_only_cohort",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Keep pilot allowlisted and define production-limited safeguards before any rollout execution.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "runtime_env_drift",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Re-run runtime smoke and endpoint readiness checks in each next PRD stage.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "prompt_bloat_under_real_long_context",
            "severity": "low",
            "status": "accepted",
            "mitigation": "Keep prompt delta limits and monitor long-context outliers in supervised telemetry.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "unexpected_diagnostic_center_divergence",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Retain trace-only Diagnostic Center mode and compare-layer observability gates.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "rollback_operator_error",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Enforce rollback-first operator checklist with explicit force-disabled verification.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "trace_artifact_leakage",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Continue sanitized artifact policy and run artifact encoding/hygiene validator each cycle.",
            "blocks_next_step": False,
        },
        {
            "risk_id": "overfitting_to_eval_fixtures",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Add broader scenario variance in planning PRD while preserving no-effect gates.",
            "blocks_next_step": False,
        },
    ]


def execute_consolidation(*, strict: bool, parsed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    a_scorecard = _safe_dict(parsed.get("a_scorecard"))
    b_scorecard = _safe_dict(parsed.get("b_scorecard"))
    a_comparison = _safe_dict(parsed.get("a_comparison"))
    b_comparison = _safe_dict(parsed.get("b_comparison"))
    a_normal = _safe_dict(parsed.get("a_normal_no_effect"))
    b_normal = _safe_dict(parsed.get("b_normal_no_effect"))
    a_rollback = _safe_dict(parsed.get("a_rollback"))
    b_rollback = _safe_dict(parsed.get("b_rollback"))
    a_mutation = _safe_dict(parsed.get("a_no_mutation"))
    b_mutation = _safe_dict(parsed.get("b_no_mutation"))
    a_hygiene = _safe_dict(parsed.get("a_encoding_hygiene"))
    b_hygiene = _safe_dict(parsed.get("b_encoding_hygiene"))

    blockers: list[str] = []
    warnings: list[str] = []

    a_passed = str(a_scorecard.get("final_status", "blocked")) == "passed"
    b_passed = str(b_scorecard.get("final_status", "blocked")) == "passed"
    a_continue = str(a_scorecard.get("decision", "stop")) == "continue_supervised"
    b_continue = str(b_scorecard.get("decision", "stop")) == "continue_supervised"

    source_cycles_passed = a_passed and b_passed
    both_cycles_continue_supervised = a_continue and b_continue
    if not a_passed:
        blockers.append("source_a_not_passed")
    if not b_passed:
        blockers.append("source_b_not_passed")
    if not a_continue:
        blockers.append("source_a_not_continue_supervised")
    if not b_continue:
        blockers.append("source_b_not_continue_supervised")

    total_test_apply_applied_count = _as_int(a_scorecard.get("test_apply_applied_count"), 0) + _as_int(
        b_scorecard.get("test_apply_applied_count"), 0
    )
    total_cases_compared = _as_int(a_comparison.get("cases_compared"), 0) + _as_int(b_comparison.get("cases_compared"), 0)
    max_cohort_size_seen = max(_as_int(a_scorecard.get("cohort_size"), 0), _as_int(b_scorecard.get("cohort_size"), 0))

    normal_user_apply_total = _as_int(a_scorecard.get("normal_user_apply_count"), 0) + _as_int(
        b_scorecard.get("normal_user_apply_count"), 0
    )
    default_off_user_path_effect_total = _as_int(a_normal.get("default_off_user_path_effect_count"), 0) + _as_int(
        b_scorecard.get("default_off_user_path_effect_count"), _as_int(b_normal.get("default_off_user_path_effect_count"), 0)
    )
    rollback_failure_total = _as_int(a_scorecard.get("rollback_failure_count"), 0) + _as_int(
        b_scorecard.get("rollback_failure_count"), 0
    )
    stale_apply_after_force_disabled_total = _as_int(a_scorecard.get("stale_apply_after_force_disabled_count"), 0) + _as_int(
        b_scorecard.get("stale_apply_after_force_disabled_count"), 0
    )
    candidate_weaker_than_baseline_total = _as_int(a_scorecard.get("candidate_weaker_than_baseline_count"), 0) + _as_int(
        b_scorecard.get("candidate_weaker_than_baseline_count"), 0
    )
    safety_regression_total = _as_int(a_scorecard.get("safety_regression_count"), 0) + _as_int(
        b_scorecard.get("safety_regression_count"), 0
    )
    kb_policy_regression_total = _as_int(a_scorecard.get("kb_policy_regression_count"), 0) + _as_int(
        b_scorecard.get("kb_policy_regression_count"), 0
    )
    prompt_bloat_regression_total = _as_int(a_scorecard.get("prompt_bloat_regression_count"), 0) + _as_int(
        b_scorecard.get("prompt_bloat_regression_count"), 0
    )
    constraint_conflict_regression_total = _as_int(a_scorecard.get("constraint_conflict_regression_count"), 0) + _as_int(
        b_scorecard.get("constraint_conflict_regression_count"), 0
    )
    raw_kb_text_exposure_total = _as_int(a_scorecard.get("raw_kb_text_exposure_count"), 0) + _as_int(
        b_scorecard.get("raw_kb_text_exposure_count"), 0
    )
    internal_only_exposure_total = _as_int(a_scorecard.get("internal_only_exposure_count"), 0) + _as_int(
        b_scorecard.get("internal_only_exposure_count"), 0
    )
    not_for_direct_quote_violation_total = _as_int(a_scorecard.get("not_for_direct_quote_violation_count"), 0) + _as_int(
        b_scorecard.get("not_for_direct_quote_violation_count"), 0
    )

    provider_called_total = _as_int(a_scorecard.get("provider_called_by_execution_count"), 0) + _as_int(
        b_scorecard.get("provider_called_by_continuation_count"), 0
    )

    production_mutation_detected_any = (
        _as_bool(a_scorecard.get("production_mutation_detected"), False)
        or _as_bool(b_scorecard.get("production_mutation_detected"), False)
        or _as_bool(a_mutation.get("all_blocks_merged_mutated"), False)
        or _as_bool(a_mutation.get("registry_mutated"), False)
        or _as_bool(a_mutation.get("config_mutated"), False)
        or _as_bool(b_mutation.get("all_blocks_merged_mutated"), False)
        or _as_bool(b_mutation.get("registry_mutated"), False)
        or _as_bool(b_mutation.get("config_mutated"), False)
    )
    artifact_encoding_hygiene_all_passed = (
        str(a_hygiene.get("final_status", "failed")) == "passed"
        and str(b_hygiene.get("final_status", "failed")) == "passed"
    )

    aggregate = PromptConstraintSupervisedAggregateMetricsV1(
        cycles_total=2,
        cycles_passed=int(a_passed) + int(b_passed),
        total_test_apply_applied_count=total_test_apply_applied_count,
        total_cases_compared=total_cases_compared,
        max_cohort_size_seen=max_cohort_size_seen,
        normal_user_apply_total=normal_user_apply_total,
        default_off_user_path_effect_total=default_off_user_path_effect_total,
        rollback_failure_total=rollback_failure_total,
        stale_apply_after_force_disabled_total=stale_apply_after_force_disabled_total,
        candidate_weaker_than_baseline_total=candidate_weaker_than_baseline_total,
        safety_regression_total=safety_regression_total,
        kb_policy_regression_total=kb_policy_regression_total,
        prompt_bloat_regression_total=prompt_bloat_regression_total,
        constraint_conflict_regression_total=constraint_conflict_regression_total,
        raw_kb_text_exposure_total=raw_kb_text_exposure_total,
        internal_only_exposure_total=internal_only_exposure_total,
        not_for_direct_quote_violation_total=not_for_direct_quote_violation_total,
        provider_called_total=provider_called_total,
        production_mutation_detected_any=production_mutation_detected_any,
        artifact_encoding_hygiene_all_passed=artifact_encoding_hygiene_all_passed,
    ).to_dict()

    reproducibility = {
        "schema_version": "prompt_constraint_supervised_consolidation_reproducibility_v1",
        "prd": PRD,
        "both_cycles_passed": source_cycles_passed,
        "both_cycles_continue_supervised": both_cycles_continue_supervised,
        "normal_user_no_effect_repeated": normal_user_apply_total == 0 and default_off_user_path_effect_total == 0,
        "rollback_success_repeated": rollback_failure_total == 0 and stale_apply_after_force_disabled_total == 0,
        "no_safety_regression_repeated": safety_regression_total == 0,
        "no_kb_regression_repeated": kb_policy_regression_total == 0,
        "no_prompt_bloat_repeated": prompt_bloat_regression_total == 0,
        "no_constraint_conflict_repeated": constraint_conflict_regression_total == 0,
        "no_raw_kb_exposure_repeated": raw_kb_text_exposure_total == 0,
        "provider_free_repeated": provider_called_total == 0,
        "no_mutation_repeated": not production_mutation_detected_any,
    }
    reproducibility["reproducibility_passed"] = all(
        bool(reproducibility[key])
        for key in (
            "both_cycles_passed",
            "both_cycles_continue_supervised",
            "normal_user_no_effect_repeated",
            "rollback_success_repeated",
            "no_safety_regression_repeated",
            "no_kb_regression_repeated",
            "no_prompt_bloat_repeated",
            "no_constraint_conflict_repeated",
            "no_raw_kb_exposure_repeated",
            "provider_free_repeated",
            "no_mutation_repeated",
        )
    )

    risks = _risk_register()
    blocking_risk_count = sum(1 for item in risks if bool(item.get("blocks_next_step", False)) or item.get("status") == "blocking")
    risk_register = PromptConstraintSupervisedRiskRegisterV1(
        risks=risks,
        blocking_risk_count=blocking_risk_count,
        risk_register_has_blockers=blocking_risk_count > 0,
    ).to_dict()

    aggregate_metrics_passed = (
        total_test_apply_applied_count >= 9
        and total_cases_compared >= 9
        and normal_user_apply_total == 0
        and default_off_user_path_effect_total == 0
        and rollback_failure_total == 0
        and stale_apply_after_force_disabled_total == 0
        and candidate_weaker_than_baseline_total == 0
        and safety_regression_total == 0
        and kb_policy_regression_total == 0
        and prompt_bloat_regression_total == 0
        and constraint_conflict_regression_total == 0
        and raw_kb_text_exposure_total == 0
        and internal_only_exposure_total == 0
        and not_for_direct_quote_violation_total == 0
        and provider_called_total == 0
        and not production_mutation_detected_any
        and artifact_encoding_hygiene_all_passed
    )

    hard_abort = (
        normal_user_apply_total > 0
        or rollback_failure_total > 0
        or raw_kb_text_exposure_total > 0
        or internal_only_exposure_total > 0
        or not_for_direct_quote_violation_total > 0
        or safety_regression_total > 0
        or kb_policy_regression_total > 0
        or production_mutation_detected_any
    )

    if strict and blockers:
        hard_abort = True

    if hard_abort:
        final_status = "blocked"
        decision = "stop"
        recommended_next_prd = "PRD-046.1.11-STOP - Prompt-Constraint Pilot Stop / Rollback Hardening v1"
    elif not source_cycles_passed or not both_cycles_continue_supervised or not reproducibility["reproducibility_passed"]:
        final_status = "blocked"
        decision = "hotfix_required"
        recommended_next_prd = "PRD-046.1.11-HF1 - Supervised Consolidation Gate Hotfix v1"
    elif risk_register["risk_register_has_blockers"]:
        final_status = "passed"
        decision = "stay_supervised"
        recommended_next_prd = "PRD-046.1.11-HF1 - Supervised Consolidation Evidence Expansion v1"
    elif aggregate_metrics_passed:
        final_status = "passed"
        decision = "prepare_production_limited_rollout_plan"
        recommended_next_prd = "PRD-046.1.12 - Production-Limited Prompt-Constraint Pilot Rollout Plan v1"
    else:
        final_status = "passed"
        decision = "stay_supervised"
        recommended_next_prd = "PRD-046.1.11-HF1 - Supervised Consolidation Evidence Expansion v1"
        warnings.append("aggregate_evidence_not_sufficient")

    decision_gate = PromptConstraintRolloutDecisionGateV1(
        final_status=final_status,
        decision=decision,
        source_cycles_passed=source_cycles_passed,
        aggregate_metrics_passed=aggregate_metrics_passed,
        reproducibility_passed=bool(reproducibility.get("reproducibility_passed", False)),
        risk_register_has_blockers=bool(risk_register["risk_register_has_blockers"]),
        normal_user_apply_total=normal_user_apply_total,
        rollback_failure_total=rollback_failure_total,
        safety_regression_total=safety_regression_total,
        kb_policy_regression_total=kb_policy_regression_total,
        raw_kb_text_exposure_total=raw_kb_text_exposure_total,
        provider_called_total=provider_called_total,
        production_mutation_detected_any=production_mutation_detected_any,
        recommended_next_prd=recommended_next_prd,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()

    decision_payload = PromptConstraintRolloutDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()

    source_cycles = [
        PromptConstraintSupervisedCycleEvidenceV1(
            prd=SOURCE_A_PRD,
            final_status=str(a_scorecard.get("final_status", "blocked")),
            decision=str(a_scorecard.get("decision", "stop")),
            cohort_size=_as_int(a_scorecard.get("cohort_size"), 0),
            test_apply_applied_count=_as_int(a_scorecard.get("test_apply_applied_count"), 0),
            cases_compared=_as_int(a_comparison.get("cases_compared"), 0),
        ),
        PromptConstraintSupervisedCycleEvidenceV1(
            prd=SOURCE_B_PRD,
            final_status=str(b_scorecard.get("final_status", "blocked")),
            decision=str(b_scorecard.get("decision", "stop")),
            cohort_size=_as_int(b_scorecard.get("cohort_size"), 0),
            test_apply_applied_count=_as_int(b_scorecard.get("test_apply_applied_count"), 0),
            cases_compared=_as_int(b_comparison.get("cases_compared"), 0),
        ),
    ]

    manifest = {
        "prd": PRD,
        "schema_version": "prompt_constraint_supervised_consolidation_manifest_v1",
        "source_cycles": [
            {"prd": SOURCE_A_PRD, "final_status": source_cycles[0].final_status, "decision": source_cycles[0].decision},
            {"prd": SOURCE_B_PRD, "final_status": source_cycles[1].final_status, "decision": source_cycles[1].decision},
        ],
        "consolidation_mode": "evidence_only_no_execution",
        "provider_allowed": False,
        "production_mutation_allowed": False,
        "source_cycles_passed": source_cycles_passed,
        "generated_at": _utc_now(),
    }

    run_payload = PromptConstraintSupervisedConsolidationRunV1(
        source_cycles=source_cycles,
        aggregate_metrics=aggregate,
        reproducibility=reproducibility,
        risk_register=risk_register,
        decision_gate=decision_gate,
        decision=decision,
    ).to_dict()

    return manifest, aggregate, reproducibility, risk_register, decision_gate, decision_payload, run_payload
