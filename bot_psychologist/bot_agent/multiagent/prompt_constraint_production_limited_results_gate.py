"""PRD-046.1.14 production-limited post-run results gate (provider-free, no new execution)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.prompt_constraint_production_limited_results_gate_v1 import (
    PromptConstraintProductionLimitedNormalUserSummaryV1,
    PromptConstraintProductionLimitedPostRunRiskRegisterV1,
    PromptConstraintProductionLimitedQualitySummaryV1,
    PromptConstraintProductionLimitedResultsDecisionV1,
    PromptConstraintProductionLimitedResultsGateV1,
    PromptConstraintProductionLimitedRollbackSummaryV1,
    PromptConstraintProductionLimitedSourceEvidenceV1,
)


PRD = "PRD-046.1.14"
SOURCE_PRD = "PRD-046.1.13"
NEXT_PRD_READY = "PRD-046.1.15 - Diagnostic Center stabilization / cleanup / eval harness consolidation"
NEXT_PRD_STAY = "PRD-046.1.14-HF1 - Production-Limited Results Evidence Expansion v1"
NEXT_PRD_HOTFIX = "PRD-046.1.14-HF1 - Production-Limited Results Gate Hotfix v1"
NEXT_PRD_STOP = "PRD-046.1.14-STOP - Prompt-Constraint Pilot Stop / Emergency Rollback Hardening v1"

REQUIRED_RISK_IDS = {
    "single_synthetic_operator_target_only",
    "limited_real_user_evidence",
    "operator_error_risk",
    "rollback_drift_risk",
    "trace_leakage_risk",
    "long_context_prompt_bloat_risk",
    "future_real_user_variability",
    "eval_harness_accumulation_cleanup_risk",
}


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
        "execution_manifest": source_dir / "production_limited_execution_manifest.json",
        "preflight_result": source_dir / "production_limited_preflight_result.json",
        "trace_samples": source_dir / "production_limited_trace_samples.json",
        "baseline_vs_test_apply": source_dir / "production_limited_baseline_vs_test_apply.json",
        "normal_user_no_effect": source_dir / "production_limited_normal_user_no_effect.json",
        "rollback_proof": source_dir / "production_limited_rollback_proof.json",
        "monitoring_scorecard": source_dir / "production_limited_monitoring_scorecard.json",
        "no_mutation_proof": source_dir / "no_mutation_proof.json",
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
        "schema_version": "prompt_constraint_production_limited_results_gate_no_mutation_proof_v1",
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
        "provider_called_by_results_gate": False,
        "new_execution_performed": False,
    }


def build_default_risk_register() -> list[dict[str, Any]]:
    return [
        {
            "risk_id": "single_synthetic_operator_target_only",
            "severity": "medium",
            "status": "accepted",
            "mitigation": "Keep default-off policy and avoid broad rollout in this stage.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "limited_real_user_evidence",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Collect additional limited evidence only if required by later gate.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "operator_error_risk",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Retain strict checklist and explicit rollback-first step ordering.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "rollback_drift_risk",
            "severity": "low",
            "status": "accepted",
            "mitigation": "Keep force-disabled absolute-priority invariant in all follow-up gates.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "trace_leakage_risk",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Continue sanitized artifact policy and encoding hygiene validation.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "long_context_prompt_bloat_risk",
            "severity": "low",
            "status": "accepted",
            "mitigation": "Preserve prompt delta checks and monitor future long-context cohorts.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "future_real_user_variability",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Use staged rollout strategy and strict gates before any wider exposure.",
            "blocks_stabilization": False,
        },
        {
            "risk_id": "eval_harness_accumulation_cleanup_risk",
            "severity": "medium",
            "status": "needs_mitigation",
            "mitigation": "Run dedicated stabilization/cleanup PRD to classify archive/runtime artifacts.",
            "blocks_stabilization": False,
        },
    ]


def execute_results_gate(*, strict: bool, parsed: dict[str, Any], risk_entries: list[dict[str, Any]] | None = None) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    execution_manifest = _safe_dict(parsed.get("execution_manifest"))
    baseline_vs_test_apply = _safe_dict(parsed.get("baseline_vs_test_apply"))
    normal_user_no_effect = _safe_dict(parsed.get("normal_user_no_effect"))
    rollback_proof = _safe_dict(parsed.get("rollback_proof"))
    monitoring_scorecard = _safe_dict(parsed.get("monitoring_scorecard"))
    trace_samples = _safe_dict(parsed.get("trace_samples"))
    source_no_mutation = _safe_dict(parsed.get("no_mutation_proof"))
    source_hygiene = _safe_dict(parsed.get("encoding_hygiene"))

    blockers: list[str] = []
    warnings: list[str] = []

    source_final_status = str(monitoring_scorecard.get("final_status", "blocked"))
    source_decision = str(monitoring_scorecard.get("decision", "stop"))
    source_execution_window_count = _as_int(execution_manifest.get("execution_window_count"), 0)
    source_target_user_count = _as_int(execution_manifest.get("target_user_count"), 0)
    source_production_limited_apply_count = _as_int(
        monitoring_scorecard.get("production_limited_apply_count", execution_manifest.get("results", {}).get("production_limited_apply_count", 0)),
        0,
    )

    source_execution_gate_passed = (
        source_final_status == "passed"
        and source_decision == "continue_limited"
        and source_execution_window_count == 1
        and source_target_user_count == 1
        and _as_bool(monitoring_scorecard.get("target_user_limit_respected"), False)
        and source_production_limited_apply_count >= 1
    )

    if source_final_status != "passed":
        blockers.append("source_final_status_not_passed")
    if source_decision != "continue_limited":
        blockers.append("source_decision_not_continue_limited")
    if source_execution_window_count != 1:
        blockers.append("source_execution_window_count_not_one")
    if source_target_user_count > 1:
        blockers.append("source_target_user_count_exceeds_one")
    if source_production_limited_apply_count < 1:
        blockers.append("source_production_limited_apply_count_below_one")

    source_evidence = PromptConstraintProductionLimitedSourceEvidenceV1(
        source_execution_prd=SOURCE_PRD,
        source_final_status=source_final_status,
        source_decision=source_decision,
        source_execution_window_count=source_execution_window_count,
        source_target_user_count=source_target_user_count,
        source_production_limited_apply_count=source_production_limited_apply_count,
    ).to_dict()

    quality_summary = PromptConstraintProductionLimitedQualitySummaryV1(
        cases_compared=_as_int(baseline_vs_test_apply.get("cases_compared"), 0),
        production_limited_apply_count=_as_int(baseline_vs_test_apply.get("production_limited_apply_count"), 0),
        candidate_weaker_than_baseline_count=_as_int(baseline_vs_test_apply.get("candidate_weaker_than_baseline_count"), 0),
        safety_regression_count=_as_int(baseline_vs_test_apply.get("safety_regression_count"), 0),
        kb_policy_regression_count=_as_int(baseline_vs_test_apply.get("kb_policy_regression_count"), 0),
        prompt_bloat_regression_count=_as_int(baseline_vs_test_apply.get("prompt_bloat_regression_count"), 0),
        constraint_conflict_regression_count=_as_int(baseline_vs_test_apply.get("constraint_conflict_regression_count"), 0),
        raw_kb_text_exposure_count=_as_int(baseline_vs_test_apply.get("raw_kb_text_exposure_count"), 0),
        internal_only_exposure_count=_as_int(baseline_vs_test_apply.get("internal_only_exposure_count"), 0),
        not_for_direct_quote_violation_count=_as_int(baseline_vs_test_apply.get("not_for_direct_quote_violation_count"), 0),
        provider_called_by_execution_count=_as_int(baseline_vs_test_apply.get("provider_called_by_execution_count"), 0),
        quality_gate_passed=False,
    ).to_dict()
    quality_summary["quality_gate_passed"] = (
        quality_summary["cases_compared"] >= 1
        and quality_summary["production_limited_apply_count"] >= 1
        and quality_summary["candidate_weaker_than_baseline_count"] == 0
        and quality_summary["safety_regression_count"] == 0
        and quality_summary["kb_policy_regression_count"] == 0
        and quality_summary["prompt_bloat_regression_count"] == 0
        and quality_summary["constraint_conflict_regression_count"] == 0
        and quality_summary["raw_kb_text_exposure_count"] == 0
        and quality_summary["internal_only_exposure_count"] == 0
        and quality_summary["not_for_direct_quote_violation_count"] == 0
        and quality_summary["provider_called_by_execution_count"] == 0
    )

    rollback_summary = PromptConstraintProductionLimitedRollbackSummaryV1(
        rollback_cases_total=_as_int(rollback_proof.get("rollback_cases_total"), 0),
        rollback_cases_passed=_as_int(rollback_proof.get("rollback_cases_passed"), 0),
        rollback_failure_count=_as_int(rollback_proof.get("rollback_failure_count"), 0),
        stale_apply_after_force_disabled_count=_as_int(rollback_proof.get("stale_apply_after_force_disabled_count"), 0),
        force_disabled_absolute_priority=_as_bool(rollback_proof.get("force_disabled_absolute_priority"), False),
        allowlisted_target_apply_after_rollback=_as_int(rollback_proof.get("allowlisted_target_apply_after_rollback"), 0),
        rollback_gate_passed=False,
    ).to_dict()
    rollback_summary["rollback_gate_passed"] = (
        rollback_summary["rollback_cases_total"] >= 1
        and rollback_summary["rollback_cases_passed"] >= 1
        and rollback_summary["rollback_failure_count"] == 0
        and rollback_summary["stale_apply_after_force_disabled_count"] == 0
        and rollback_summary["force_disabled_absolute_priority"] is True
        and rollback_summary["allowlisted_target_apply_after_rollback"] == 0
    )

    normal_user_summary = PromptConstraintProductionLimitedNormalUserSummaryV1(
        normal_user_cases_total=_as_int(normal_user_no_effect.get("normal_user_cases_total"), 0),
        normal_user_apply_count=_as_int(normal_user_no_effect.get("normal_user_apply_count"), 0),
        default_off_user_path_effect_count=_as_int(normal_user_no_effect.get("default_off_user_path_effect_count"), 0),
        normal_user_prompt_changed_by_pilot_count=_as_int(normal_user_no_effect.get("normal_user_prompt_changed_by_pilot_count"), 0),
        normal_user_final_answer_changed_by_pilot_count=_as_int(normal_user_no_effect.get("normal_user_final_answer_changed_by_pilot_count"), 0),
        normal_user_gate_passed=False,
    ).to_dict()
    normal_user_summary["normal_user_gate_passed"] = (
        normal_user_summary["normal_user_cases_total"] >= 2
        and normal_user_summary["normal_user_apply_count"] == 0
        and normal_user_summary["default_off_user_path_effect_count"] == 0
        and normal_user_summary["normal_user_prompt_changed_by_pilot_count"] == 0
        and normal_user_summary["normal_user_final_answer_changed_by_pilot_count"] == 0
    )

    samples = _safe_list(trace_samples.get("samples"))
    raw_prompt_saved_count = 0
    raw_kb_text_saved_count = 0
    private_user_text_saved_count = 0
    secret_like_value_count = 0
    provider_payload_dump_count = 0

    for row in samples:
        item = _safe_dict(row)
        raw_prompt_saved_count += int(bool(item.get("raw_prompt_saved")))
        raw_kb_text_saved_count += int(bool(item.get("raw_kb_text_exposed")))
        private_user_text_saved_count += int(bool(item.get("private_user_text_saved")))
        provider_payload_dump_count += int(bool(item.get("provider_payload_dumped")))
        for key in item.keys():
            key_text = str(key).lower()
            if "secret" in key_text or "token" in key_text or "api_key" in key_text:
                secret_like_value_count += 1

    trace_sanitization_failed = (
        raw_prompt_saved_count > 0
        or raw_kb_text_saved_count > 0
        or private_user_text_saved_count > 0
        or secret_like_value_count > 0
        or provider_payload_dump_count > 0
        or _as_bool(monitoring_scorecard.get("trace_sanitization_failed"), False)
    )

    trace_sanitization_summary = {
        "trace_samples_checked": len(samples),
        "raw_prompt_saved_count": raw_prompt_saved_count,
        "raw_kb_text_saved_count": raw_kb_text_saved_count,
        "private_user_text_saved_count": private_user_text_saved_count,
        "secret_like_value_count": secret_like_value_count,
        "provider_payload_dump_count": provider_payload_dump_count,
        "trace_sanitization_failed": trace_sanitization_failed,
        "trace_sanitization_gate_passed": not trace_sanitization_failed,
    }

    risks = risk_entries if risk_entries is not None else build_default_risk_register()
    risk_ids = {str(item.get("risk_id", "")) for item in risks}
    missing_risks = REQUIRED_RISK_IDS.difference(risk_ids)
    if missing_risks:
        blockers.append("risk_register_missing_required_risks")

    blocking_risk_count = sum(
        1
        for item in risks
        if _as_bool(item.get("blocks_stabilization"), False) or str(item.get("status", "")).strip().lower() == "blocking"
    )
    risk_register = PromptConstraintProductionLimitedPostRunRiskRegisterV1(
        risks=risks,
        blocking_risk_count=blocking_risk_count,
        risk_register_has_blockers=blocking_risk_count > 0,
    ).to_dict()

    no_mutation_flags = {
        "all_blocks_merged_mutated": _as_bool(source_no_mutation.get("all_blocks_merged_mutated"), False),
        "registry_mutated": _as_bool(source_no_mutation.get("registry_mutated"), False),
        "config_mutated": _as_bool(source_no_mutation.get("config_mutated"), False),
        "chroma_reindex_performed": _as_bool(source_no_mutation.get("chroma_reindex_performed"), False),
        "production_apply_performed": _as_bool(source_no_mutation.get("production_apply_performed"), False),
    }
    production_mutation_detected = any(no_mutation_flags.values())

    artifact_encoding_hygiene_passed = str(source_hygiene.get("final_status", "failed")) == "passed"

    hard_abort = (
        normal_user_summary["normal_user_apply_count"] > 0
        or normal_user_summary["default_off_user_path_effect_count"] > 0
        or rollback_summary["rollback_failure_count"] > 0
        or rollback_summary["stale_apply_after_force_disabled_count"] > 0
        or quality_summary["safety_regression_count"] > 0
        or quality_summary["kb_policy_regression_count"] > 0
        or quality_summary["raw_kb_text_exposure_count"] > 0
        or quality_summary["internal_only_exposure_count"] > 0
        or quality_summary["not_for_direct_quote_violation_count"] > 0
        or trace_sanitization_summary["trace_sanitization_failed"]
        or production_mutation_detected
    )
    if strict and blockers:
        hard_abort = True

    ready_for_stabilization_cleanup = (
        source_execution_gate_passed
        and quality_summary["quality_gate_passed"]
        and rollback_summary["rollback_gate_passed"]
        and normal_user_summary["normal_user_gate_passed"]
        and trace_sanitization_summary["trace_sanitization_gate_passed"]
        and not risk_register["risk_register_has_blockers"]
        and not production_mutation_detected
        and artifact_encoding_hygiene_passed
    )

    if hard_abort:
        final_status = "blocked"
        decision = "stop"
        recommended_next_prd = NEXT_PRD_STOP
    elif ready_for_stabilization_cleanup:
        final_status = "passed"
        decision = "ready_for_stabilization_cleanup"
        recommended_next_prd = NEXT_PRD_READY
    elif quality_summary["quality_gate_passed"] and rollback_summary["rollback_gate_passed"] and normal_user_summary["normal_user_gate_passed"]:
        final_status = "passed"
        decision = "stay_limited"
        recommended_next_prd = NEXT_PRD_STAY
        warnings.append("stabilization_readiness_not_full")
    else:
        final_status = "needs_hotfix"
        decision = "hotfix_required"
        recommended_next_prd = NEXT_PRD_HOTFIX

    decision_gate = {
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_execution_gate_passed": source_execution_gate_passed,
        "quality_gate_passed": quality_summary["quality_gate_passed"],
        "rollback_gate_passed": rollback_summary["rollback_gate_passed"],
        "normal_user_gate_passed": normal_user_summary["normal_user_gate_passed"],
        "trace_sanitization_gate_passed": trace_sanitization_summary["trace_sanitization_gate_passed"],
        "risk_register_has_blockers": bool(risk_register["risk_register_has_blockers"]),
        "new_execution_performed": False,
        "provider_called_by_results_gate": False,
        "production_mutation_detected": production_mutation_detected,
        "artifact_encoding_hygiene_passed": artifact_encoding_hygiene_passed,
        "recommended_next_prd": recommended_next_prd,
        "blockers": blockers,
        "warnings": warnings,
    }

    decision_payload = PromptConstraintProductionLimitedResultsDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        recommended_next_prd=recommended_next_prd,
    ).to_dict()

    gate_payload = PromptConstraintProductionLimitedResultsGateV1(
        source_evidence=source_evidence,
        quality_summary=quality_summary,
        rollback_summary=rollback_summary,
        normal_user_summary=normal_user_summary,
        trace_sanitization_summary=trace_sanitization_summary,
        post_run_risk_register=risk_register,
        decision=decision,
    ).to_dict()

    manifest = {
        "prd": PRD,
        "schema_version": "production_limited_results_manifest_v1",
        "source_execution_prd": SOURCE_PRD,
        "source_final_status": source_final_status,
        "source_decision": source_decision,
        "gate_mode": "post_run_results_only",
        "new_execution_performed": False,
        "source_execution_window_count": source_execution_window_count,
        "source_target_user_count": source_target_user_count,
        "source_production_limited_apply_count": source_production_limited_apply_count,
        "provider_allowed": False,
        "production_mutation_allowed": False,
        "generated_at": _utc_now(),
    }

    return (
        manifest,
        quality_summary,
        rollback_summary,
        normal_user_summary,
        trace_sanitization_summary,
        risk_register,
        decision_gate,
        decision_payload,
        gate_payload,
    )
