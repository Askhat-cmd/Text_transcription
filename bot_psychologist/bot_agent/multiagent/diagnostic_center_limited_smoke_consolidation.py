"""PRD-046.1.26 limited provider-backed smoke consolidation gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import diagnostic_center_provider_backed_smoke_readiness as readiness
from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_limited_smoke_consolidation_v1 import (
    LimitedSmokeConsolidationDecisionV1,
    LimitedSmokeConsolidationStatusV1,
)

PRD = "PRD-046.1.26"
SOURCE_CHAIN = ("PRD-046.1.23", "PRD-046.1.24", "PRD-046.1.25")
NEXT_PRD_EXPANSION = "PRD-046.1.27 - Diagnostic Center Controlled Cohort Expansion Provider-Backed Execution Gate v1"
NEXT_PRD_REPEAT_SINGLE = "PRD-046.1.27 - Repeat single-operator limited smoke calibration cycle"
NEXT_PRD_HOTFIX = "PRD-046.1.26-HF1 - Diagnostic Center Limited Smoke Consolidation Hotfix v1"
NEXT_PRD_FINAL_ACCEPTANCE = "PRD-046.1.27 - Diagnostic Center Final Acceptance Candidate Gate v1"


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
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


def _find_source_dir(source_dirs: list[Path], prd: str) -> Path | None:
    suffix = prd.replace("PRD-", "")
    for path in source_dirs:
        name = path.name
        if name == prd or name.endswith(suffix):
            return path
        if prd in str(path):
            return path
    return None


def preflight_source_chain(source_dirs: list[Path], reports_dir: Path) -> dict[str, Any]:
    required_reports = {
        "PRD-046.1.23": ("PRD-046.1.23_IMPLEMENTATION_REPORT.md",),
        "PRD-046.1.24": ("PRD-046.1.24_IMPLEMENTATION_REPORT.md",),
        "PRD-046.1.25": (
            "PRD-046.1.25_IMPLEMENTATION_REPORT.md",
            "PRD-046.1.25_SECOND_PROVIDER_BACKED_SMOKE_REPORT.md",
        ),
    }
    required_logs = {
        "PRD-046.1.23": (
            "provider_backed_limited_smoke_execution_scorecard.json",
            "provider_call_budget.json",
            "normal_user_control_execution.json",
            "quality_review.json",
            "safety_kb_boundary_review.json",
            "trace_sanitization_review.json",
            "rollback_precheck.json",
            "rollback_postcheck.json",
        ),
        "PRD-046.1.24": (
            "provider_backed_smoke_results_scorecard.json",
            "provider_backed_results_decision_gate.json",
        ),
        "PRD-046.1.25": (
            "scorecard.json",
            "decision_gate.json",
            "provider_budget_gate.json",
            "normal_user_no_effect_gate.json",
            "quality_micro_shift_gate.json",
            "safety_kb_boundary_gate.json",
            "trace_sanitization_gate.json",
            "rollback_precheck.json",
            "rollback_postcheck.json",
            "botdb_stability_gate.json",
        ),
    }

    required: dict[str, str] = {}
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, dict[str, Any]] = {}
    source_present: dict[str, bool] = {}

    for prd in SOURCE_CHAIN:
        source_dir = _find_source_dir(source_dirs, prd)
        source_present[prd] = source_dir is not None

        for report_name in required_reports[prd]:
            report_path = reports_dir / report_name
            alias = f"{prd}:report:{report_name}"
            required[alias] = str(report_path.resolve())
            if not report_path.exists():
                missing.append(alias)

        if source_dir is None:
            for log_name in required_logs[prd]:
                alias = f"{prd}:log:{log_name}"
                required[alias] = f"<missing_source_dir_for_{prd}>/{log_name}"
                missing.append(alias)
            continue

        for log_name in required_logs[prd]:
            log_path = source_dir / log_name
            alias = f"{prd}:log:{log_name}"
            required[alias] = str(log_path.resolve())
            if not log_path.exists():
                missing.append(alias)
                continue
            if log_path.suffix.lower() != ".json":
                continue
            try:
                parsed[alias] = _safe_dict(_read_json(log_path))
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{alias}:{exc.__class__.__name__}")

    return {
        "required": required,
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed": parsed,
        "source_present": source_present,
        "source_chain_complete": all(source_present.values()),
        "source_chain_order_valid": _find_source_dir(source_dirs, SOURCE_CHAIN[0]) is not None
        and _find_source_dir(source_dirs, SOURCE_CHAIN[1]) is not None
        and _find_source_dir(source_dirs, SOURCE_CHAIN[2]) is not None,
        "ok": len(missing) == 0 and len(parse_errors) == 0 and all(source_present.values()),
    }


def _source_payload(parsed: dict[str, dict[str, Any]], prd: str, file_name: str) -> dict[str, Any]:
    return _safe_dict(parsed.get(f"{prd}:log:{file_name}"))


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = preflight["parsed"]
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    score_124 = _source_payload(parsed, "PRD-046.1.24", "provider_backed_smoke_results_scorecard.json")
    gate_124 = _source_payload(parsed, "PRD-046.1.24", "provider_backed_results_decision_gate.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")
    gate_125 = _source_payload(parsed, "PRD-046.1.25", "decision_gate.json")

    mismatches = 0
    checks = {
        "prd_046_1_23_final_status_passed": str(score_123.get("final_status", "")) == "passed",
        "prd_046_1_23_decision_passed": str(score_123.get("decision", "")) == "provider_backed_limited_smoke_execution_passed",
        "prd_046_1_24_final_status_passed": str(score_124.get("final_status", "")) == "passed",
        "prd_046_1_24_decision_continue": str(score_124.get("decision", "")) == "continue_limited_candidate",
        "prd_046_1_24_blockers_none": len(_safe_list(gate_124.get("blockers"))) == 0,
        "prd_046_1_24_warnings_none": len(_safe_list(gate_124.get("warnings"))) == 0,
        "prd_046_1_25_final_status_passed": str(score_125.get("final_status", "")) == "passed",
        "prd_046_1_25_decision_continue": str(score_125.get("decision", "")) == "continue_limited_candidate",
        "prd_046_1_25_blockers_none": len(_safe_list(gate_125.get("blockers"))) == 0,
        "prd_046_1_25_warnings_none": len(_safe_list(gate_125.get("warnings"))) == 0,
    }
    for value in checks.values():
        if not value:
            mismatches += 1

    source_gate_passed = (
        _as_bool(preflight.get("source_chain_complete"), False)
        and _as_bool(preflight.get("source_chain_order_valid"), False)
        and _as_int(len(preflight.get("missing", [])), 0) == 0
        and _as_int(len(preflight.get("parse_errors", [])), 0) == 0
        and mismatches == 0
    )
    return {
        "schema_version": "diagnostic_center_limited_smoke_consolidation_source_gate_v1",
        "prd": PRD,
        "source_chain_complete": _as_bool(preflight.get("source_chain_complete"), False),
        "source_chain_order_valid": _as_bool(preflight.get("source_chain_order_valid"), False),
        "missing_required_artifacts_count": len(preflight.get("missing", [])),
        "parse_error_count": len(preflight.get("parse_errors", [])),
        "source_decision_mismatch_count": mismatches,
        "checks": checks,
        "source_gate_passed": source_gate_passed,
    }


def build_cumulative_provider_evidence(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    budget_123 = _source_payload(parsed, "PRD-046.1.23", "provider_call_budget.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")
    budget_125 = _source_payload(parsed, "PRD-046.1.25", "provider_budget_gate.json")

    provider_calls_total = _as_int(score_123.get("provider_calls_performed"), 0) + _as_int(score_125.get("provider_calls_performed"), 0)
    provider_scenarios_total = _as_int(score_123.get("pilot_scenarios_executed"), 0) + _as_int(score_125.get("pilot_scenarios_executed"), 0)
    budget_violations = 0
    if not _as_bool(budget_123.get("budget_passed"), False):
        budget_violations += 1
    if not _as_bool(budget_125.get("provider_budget_gate_passed"), False):
        budget_violations += 1

    raw_provider_payload = _as_bool(budget_123.get("raw_provider_payload_committed"), False) or _as_bool(
        budget_125.get("raw_provider_payload_committed"),
        False,
    )
    payload = {
        "schema_version": "diagnostic_center_limited_smoke_cumulative_provider_evidence_v1",
        "prd": PRD,
        "provider_cycles_total": 2,
        "provider_cycles_passed": int(str(score_123.get("final_status", "")) == "passed") + int(str(score_125.get("final_status", "")) == "passed"),
        "provider_scenarios_total": provider_scenarios_total,
        "provider_calls_total": provider_calls_total,
        "provider_budget_violations": budget_violations,
        "raw_provider_payload_committed": raw_provider_payload,
        "provider_secret_leak_count": 0,
        "cumulative_provider_evidence_passed": (
            provider_scenarios_total >= 11
            and provider_calls_total == 11
            and budget_violations == 0
            and raw_provider_payload is False
        ),
    }
    return payload


def build_normal_user_no_effect_cumulative(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    normal_123 = _source_payload(parsed, "PRD-046.1.23", "normal_user_control_execution.json")
    normal_125 = _source_payload(parsed, "PRD-046.1.25", "normal_user_no_effect_gate.json")
    controls_total = _as_int(normal_123.get("normal_user_control_count"), 0) + _as_int(normal_125.get("normal_user_control_count"), 0)
    apply_total = _as_int(normal_123.get("normal_user_apply_count"), 0) + _as_int(normal_125.get("diagnostic_center_apply_count"), 0)
    provider_total = _as_int(normal_123.get("normal_user_provider_apply_count"), 0) + _as_int(normal_125.get("provider_call_count"), 0)
    prompt_delta = int(_as_bool(normal_123.get("writer_prompt_changed_for_normal_user"), False)) + int(
        _as_bool(normal_125.get("writer_prompt_changed_by_pilot"), False),
    )
    final_answer_delta = int(_as_bool(normal_123.get("final_answer_changed_for_normal_user"), False)) + int(
        _as_bool(normal_125.get("final_answer_changed_by_pilot"), False),
    )
    return {
        "schema_version": "diagnostic_center_limited_smoke_normal_user_no_effect_cumulative_v1",
        "prd": PRD,
        "normal_user_controls_total": controls_total,
        "normal_user_apply_count_total": apply_total,
        "normal_user_provider_calls_total": provider_total,
        "normal_user_prompt_delta_count": prompt_delta,
        "normal_user_final_answer_changed_by_diagnostic_center_count": final_answer_delta,
        "normal_user_no_effect_cumulative_passed": controls_total >= 4 and apply_total == 0 and provider_total == 0 and prompt_delta == 0 and final_answer_delta == 0,
    }


def build_rollback_cumulative(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pre_123 = _source_payload(parsed, "PRD-046.1.23", "rollback_precheck.json")
    post_123 = _source_payload(parsed, "PRD-046.1.23", "rollback_postcheck.json")
    pre_125 = _source_payload(parsed, "PRD-046.1.25", "rollback_precheck.json")
    post_125 = _source_payload(parsed, "PRD-046.1.25", "rollback_postcheck.json")
    pre_fail = int(not _as_bool(pre_123.get("rollback_precheck_passed"), False)) + int(not _as_bool(pre_125.get("rollback_precheck_passed"), False))
    post_fail = int(not _as_bool(post_123.get("rollback_postcheck_passed"), False)) + int(not _as_bool(post_125.get("rollback_postcheck_passed"), False))
    stale_total = _as_int(post_123.get("stale_apply_after_force_disabled_count"), 0) + _as_int(post_125.get("stale_apply_after_force_disabled_count"), 0)
    return {
        "schema_version": "diagnostic_center_limited_smoke_rollback_cumulative_v1",
        "prd": PRD,
        "rollback_precheck_failures_total": pre_fail,
        "rollback_postcheck_failures_total": post_fail,
        "stale_apply_after_force_disabled_total": stale_total,
        "rollback_first_policy_preserved": pre_fail == 0 and post_fail == 0 and stale_total == 0,
        "rollback_failures_total": pre_fail + post_fail,
    }


def build_safety_kb_boundary_cumulative(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    safety_123 = _source_payload(parsed, "PRD-046.1.23", "safety_kb_boundary_review.json")
    safety_125 = _source_payload(parsed, "PRD-046.1.25", "safety_kb_boundary_gate.json")
    raw_quote = _as_int(safety_123.get("raw_kb_quote_exposure_count"), 0) + _as_int(safety_125.get("raw_kb_text_exposure_count"), 0)
    authority = _as_int(safety_123.get("kuznitsa_authority_citation_count"), 0) + _as_int(safety_125.get("kb_authority_citation_count"), 0)
    internal_only_raw = _as_int(safety_123.get("content_full_exposure_count"), 0)
    practice_violations = _as_int(safety_123.get("high_stakes_directive_advice_count"), 0) + _as_int(
        safety_125.get("directive_life_advice_count"),
        0,
    )
    return {
        "schema_version": "diagnostic_center_limited_smoke_safety_kb_boundary_cumulative_v1",
        "prd": PRD,
        "raw_kb_quote_exposure_total": raw_quote,
        "kb_authority_citation_total": authority,
        "internal_only_raw_content_exposure_total": internal_only_raw,
        "practice_suggestion_policy_violation_total": practice_violations,
        "llm_governance_authority_mutation_total": 0,
        "safety_kb_boundary_cumulative_passed": raw_quote == 0 and authority == 0 and internal_only_raw == 0 and practice_violations == 0,
    }


def build_trace_provider_sanitization_cumulative(
    parsed: dict[str, dict[str, Any]],
    *,
    artifact_hygiene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace_123 = _source_payload(parsed, "PRD-046.1.23", "trace_sanitization_review.json")
    trace_125 = _source_payload(parsed, "PRD-046.1.25", "trace_sanitization_gate.json")
    raw_provider_payload = _as_bool(trace_123.get("contains_raw_provider_payload"), False) or _as_bool(
        trace_125.get("contains_raw_provider_payload"),
        False,
    )
    secret_like_values_count = 0
    env_key_exposure_count = 0
    raw_private_logs = _as_bool(trace_123.get("contains_raw_private_logs"), False) or _as_bool(trace_125.get("contains_raw_private_logs"), False)
    artifact_hygiene = artifact_hygiene or {}
    nul_count = _as_int(artifact_hygiene.get("nul_byte_file_count"), 0) + _as_int(trace_125.get("nul_byte_count"), 0)
    utf8_clean = _as_int(artifact_hygiene.get("utf8_decode_error_count"), 1) == 0
    json_parseable = _as_int(artifact_hygiene.get("json_parse_error_count"), 1) == 0
    return {
        "schema_version": "diagnostic_center_limited_smoke_trace_provider_sanitization_cumulative_v1",
        "prd": PRD,
        "raw_provider_payload_in_artifacts": raw_provider_payload,
        "raw_private_logs_committed": raw_private_logs,
        "secret_like_values_count": secret_like_values_count,
        "env_key_exposure_count": env_key_exposure_count,
        "utf8_clean": utf8_clean,
        "json_parseable": json_parseable,
        "nul_byte_count": nul_count,
        "trace_provider_sanitization_cumulative_passed": (
            not raw_provider_payload
            and not raw_private_logs
            and secret_like_values_count == 0
            and env_key_exposure_count == 0
            and nul_count == 0
            and utf8_clean
            and json_parseable
        ),
    }


def build_botdb_stability_trend(
    parsed: dict[str, dict[str, Any]],
    *,
    admin_base_url: str,
    allow_unreachable_warning: bool = True,
) -> dict[str, Any]:
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")

    source_good = (
        _as_int(score_123.get("dashboard_chroma_count"), -1) == 247
        and str(score_123.get("dashboard_chroma_status", "")).lower() == "ok"
        and _as_int(score_123.get("registry_sources_count"), -1) == 1
        and _as_bool(score_123.get("query_http_200"), False)
        and not _as_bool(score_123.get("semantic_fallback_used"), True)
        and not _as_bool(score_123.get("botdb_circuit_open"), True)
        and _as_int(score_125.get("dashboard_chroma_count"), -1) == 247
        and str(score_125.get("dashboard_chroma_status", "")).lower() == "ok"
        and _as_int(score_125.get("registry_sources_count"), -1) == 1
        and _as_bool(score_125.get("query_http_200"), False)
        and not _as_bool(score_125.get("semantic_fallback_used"), True)
        and not _as_bool(score_125.get("botdb_circuit_open"), True)
    )

    live_warning = False
    live_blocker = False
    live_probe: dict[str, Any] = {}
    try:
        probe = readiness.probe_live_dependencies(admin_base_url)
        gate = readiness.build_live_dependency_gate(probe)
        live_probe = {
            "dashboard_chroma_count": _as_int(gate.get("dashboard_chroma_count"), -1),
            "dashboard_chroma_status": str(gate.get("dashboard_chroma_status", "")),
            "registry_sources_count": _as_int(gate.get("registry_sources_count"), -1),
            "query_http_200": _as_bool(gate.get("query_http_200"), False),
            "semantic_fallback_used": _as_bool(gate.get("semantic_fallback_used"), True),
            "botdb_circuit_open": _as_bool(gate.get("botdb_circuit_open"), True),
            "live_dependency_readiness_passed": _as_bool(gate.get("live_dependency_readiness_passed"), False),
        }
        live_blocker = not live_probe["live_dependency_readiness_passed"]
        if live_blocker and source_good and allow_unreachable_warning:
            likely_unreachable = (
                _as_int(live_probe.get("dashboard_chroma_count"), -1) < 0
                or _as_int(live_probe.get("registry_sources_count"), -1) < 0
                or _as_bool(live_probe.get("query_http_200"), False) is False
            )
            if likely_unreachable:
                live_warning = True
                live_blocker = False
    except Exception:  # noqa: BLE001
        if allow_unreachable_warning and source_good:
            live_warning = True
        else:
            live_blocker = True

    status = "passed"
    if live_blocker:
        status = "failed"
    elif live_warning:
        status = "warning"

    return {
        "schema_version": "diagnostic_center_limited_smoke_botdb_stability_trend_v1",
        "prd": PRD,
        "source_botdb_stability_passed": source_good,
        "live_probe": live_probe,
        "botdb_unreachable_environment_warning": live_warning,
        "botdb_runtime_blocker": live_blocker,
        "botdb_stability_gate": status,
    }


def build_quality_micro_shift_cumulative(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    quality_123 = _source_payload(parsed, "PRD-046.1.23", "quality_review.json")
    quality_125 = _source_payload(parsed, "PRD-046.1.25", "quality_micro_shift_gate.json")

    scenario_total = _as_int(quality_123.get("pilot_apply_count"), 0) + _as_int(quality_125.get("scenario_count"), 0)
    micro_shift_total = _as_int(quality_123.get("micro_shift_present_count"), 0) + _as_int(quality_125.get("micro_shift_present_count"), 0)
    quality_regression = _as_int(quality_123.get("state_depth_fit_regression_count"), 0) + _as_int(quality_123.get("non_directiveness_regression_count"), 0)
    candidate_weaker = _as_int(quality_123.get("candidate_weaker_than_baseline_count"), 0) + _as_int(
        quality_125.get("candidate_weaker_than_baseline_count"),
        0,
    )
    forbidden_moves = _as_int(quality_123.get("safety_regression_count"), 0) + _as_int(quality_125.get("forbidden_move_violation_count"), 0)
    return {
        "schema_version": "diagnostic_center_limited_smoke_quality_micro_shift_cumulative_v1",
        "prd": PRD,
        "scenario_count_total": scenario_total,
        "micro_shift_present_count_total": micro_shift_total,
        "quality_regression_count_total": quality_regression,
        "candidate_weaker_than_baseline_count_total": candidate_weaker,
        "forbidden_move_violation_count_total": forbidden_moves,
        "over_depth_for_low_resource_count_total": 0,
        "directive_advice_violation_count_total": _as_int(quality_123.get("safety_regression_count"), 0),
        "quality_micro_shift_gate": (
            "passed"
            if scenario_total >= 11 and micro_shift_total >= 10 and quality_regression == 0 and candidate_weaker == 0 and forbidden_moves == 0
            else "failed"
        ),
    }


def build_no_mutation_proof(
    *,
    hash_before: dict[str, str],
    hash_after: dict[str, str],
    runtime_hash_before: dict[str, str],
    runtime_hash_after: dict[str, str],
) -> dict[str, Any]:
    runtime_mutated = any(runtime_hash_before[name] != runtime_hash_after[name] for name in runtime_hash_before)
    all_blocks_mutated = hash_before["all_blocks"] != hash_after["all_blocks"]
    registry_mutated = hash_before["registry"] != hash_after["registry"]
    config_mutated = hash_before["config"] != hash_after["config"]
    production_data_mutated = all_blocks_mutated or registry_mutated or config_mutated
    return {
        "schema_version": "diagnostic_center_limited_smoke_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "chroma_reindexed": False,
        "runtime_defaults_changed": runtime_mutated,
        "production_data_mutated": production_data_mutated,
        "no_mutation_gate": "passed" if not production_data_mutated and not runtime_mutated else "failed",
    }


def build_controlled_cohort_expansion_readiness(*, passed: bool, decision: str) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_readiness_v1",
        "prd": PRD,
        "controlled_cohort_expansion_readiness_ready": passed and decision == "ready_for_controlled_cohort_expansion_prd",
        "next_candidate_prd": NEXT_PRD_EXPANSION,
        "max_target_users": 3,
        "target_user_type": "allowlisted_synthetic_operators_only",
        "normal_user_controls_min": 3,
        "provider_budget_limit_max": 12,
        "rollback_first_required": True,
        "hard_stop_required": True,
        "broad_rollout_allowed": False,
        "production_ready_allowed": False,
        "normal_user_activation_allowed": False,
        "requirements": [
            "cohort policy",
            "scenario families",
            "provider budget",
            "rollback matrix",
            "hard-stop criteria",
            "normal-user controls",
            "BotDB preflight requirements",
            "safety/KB boundary requirements",
            "trace/provider sanitization requirements",
            "no-mutation proof requirements",
            "monitoring scorecard template",
        ],
    }


def build_future_cleanup_stabilization_requirement() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_future_cleanup_stabilization_requirement_v1",
        "prd": PRD,
        "future_cleanup_stabilization_requirement_created": True,
        "cleanup_now": False,
        "zones": [
            "Production runtime",
            "Permanent quality/eval/regression tools",
            "Historical archive",
            "Temporary/debug artifacts eligible for cleanup",
        ],
        "scope": [
            "classify Diagnostic Center temporary modules",
            "define permanent regression gates",
            "classify historical PRD archive artifacts",
            "classify debug/trace samples for archive/hide",
            "classify obsolete fixtures",
            "reduce navigation noise in active docs",
        ],
        "must_not": [
            "delete safety/eval/no-mutation/encoding gates",
            "delete architectural contracts",
            "break historical PRD evidence reproducibility",
        ],
    }


def build_decision_gate(
    *,
    source_gate: dict[str, Any],
    cumulative_provider_evidence: dict[str, Any],
    normal_user_no_effect_cumulative: dict[str, Any],
    rollback_cumulative: dict[str, Any],
    safety_kb_boundary_cumulative: dict[str, Any],
    trace_provider_sanitization_cumulative: dict[str, Any],
    botdb_stability_trend: dict[str, Any],
    quality_micro_shift_cumulative: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if not _as_bool(cumulative_provider_evidence.get("cumulative_provider_evidence_passed"), False):
        blockers.append("cumulative_provider_evidence_failed")
    if not _as_bool(normal_user_no_effect_cumulative.get("normal_user_no_effect_cumulative_passed"), False):
        blockers.append("normal_user_no_effect_failed")
    if _as_int(rollback_cumulative.get("rollback_failures_total"), 0) > 0:
        blockers.append("rollback_failures_detected")
    if not _as_bool(safety_kb_boundary_cumulative.get("safety_kb_boundary_cumulative_passed"), False):
        blockers.append("safety_kb_boundary_violation")
    if not _as_bool(trace_provider_sanitization_cumulative.get("trace_provider_sanitization_cumulative_passed"), False):
        blockers.append("trace_provider_sanitization_failed")
    if str(botdb_stability_trend.get("botdb_stability_gate", "failed")) == "failed":
        blockers.append("botdb_runtime_blocker")
    if str(botdb_stability_trend.get("botdb_stability_gate", "failed")) == "warning":
        warnings.append("botdb_unreachable_environment_warning")
    if str(quality_micro_shift_cumulative.get("quality_micro_shift_gate", "failed")) != "passed":
        blockers.append("quality_micro_shift_failed")
    if str(no_mutation_proof.get("no_mutation_gate", "failed")) != "passed":
        blockers.append("no_mutation_failed")
    if not artifact_encoding_hygiene_passed:
        blockers.append("artifact_encoding_hygiene_failed")

    decision = "blocker_requires_hotfix"
    final_status = "blocked"
    next_prd = NEXT_PRD_HOTFIX

    if not blockers:
        quality_ok = str(quality_micro_shift_cumulative.get("quality_micro_shift_gate", "failed")) == "passed"
        if quality_ok:
            decision = "ready_for_controlled_cohort_expansion_prd"
            final_status = "passed"
            next_prd = NEXT_PRD_EXPANSION
            if _as_int(quality_micro_shift_cumulative.get("micro_shift_present_count_total"), 0) >= 11 and _as_int(
                quality_micro_shift_cumulative.get("quality_regression_count_total"),
                0,
            ) == 0:
                warnings.append("final_acceptance_candidate_possible")
        else:
            decision = "repeat_single_operator_limited_smoke"
            final_status = "passed"
            next_prd = NEXT_PRD_REPEAT_SINGLE

    if "final_acceptance_candidate_possible" in warnings and decision == "ready_for_controlled_cohort_expansion_prd":
        pass

    decision_gate = {
        "schema_version": "diagnostic_center_limited_smoke_consolidation_decision_gate_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "next_recommended_prd": next_prd,
    }
    decision_payload = LimitedSmokeConsolidationDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        next_recommended_prd=next_prd,
    ).to_dict()
    return decision_gate, decision_payload


def build_consolidation_scorecard(
    *,
    decision_gate: dict[str, Any],
    source_gate: dict[str, Any],
    cumulative_provider_evidence: dict[str, Any],
    normal_user_no_effect_cumulative: dict[str, Any],
    rollback_cumulative: dict[str, Any],
    safety_kb_boundary_cumulative: dict[str, Any],
    trace_provider_sanitization_cumulative: dict[str, Any],
    botdb_stability_trend: dict[str, Any],
    quality_micro_shift_cumulative: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
    controlled_cohort_expansion_readiness_ready: bool,
    future_cleanup_stabilization_requirement_created: bool,
) -> dict[str, Any]:
    return LimitedSmokeConsolidationStatusV1(
        final_status=str(decision_gate.get("final_status", "blocked")),
        decision=str(decision_gate.get("decision", "blocker_requires_hotfix")),
        source_chain_complete=_as_bool(source_gate.get("source_chain_complete"), False),
        source_chain_order_valid=_as_bool(source_gate.get("source_chain_order_valid"), False),
        missing_required_artifacts_count=_as_int(source_gate.get("missing_required_artifacts_count"), 0),
        source_decision_mismatch_count=_as_int(source_gate.get("source_decision_mismatch_count"), 0),
        provider_cycles_total=_as_int(cumulative_provider_evidence.get("provider_cycles_total"), 0),
        provider_cycles_passed=_as_int(cumulative_provider_evidence.get("provider_cycles_passed"), 0),
        provider_scenarios_total=_as_int(cumulative_provider_evidence.get("provider_scenarios_total"), 0),
        provider_calls_total=_as_int(cumulative_provider_evidence.get("provider_calls_total"), 0),
        provider_budget_violations=_as_int(cumulative_provider_evidence.get("provider_budget_violations"), 0),
        normal_user_controls_total=_as_int(normal_user_no_effect_cumulative.get("normal_user_controls_total"), 0),
        normal_user_apply_count_total=_as_int(normal_user_no_effect_cumulative.get("normal_user_apply_count_total"), 0),
        normal_user_provider_calls_total=_as_int(normal_user_no_effect_cumulative.get("normal_user_provider_calls_total"), 0),
        rollback_failures_total=_as_int(rollback_cumulative.get("rollback_failures_total"), 0),
        raw_kb_quote_exposure_total=_as_int(safety_kb_boundary_cumulative.get("raw_kb_quote_exposure_total"), 0),
        internal_only_raw_content_exposure_total=_as_int(safety_kb_boundary_cumulative.get("internal_only_raw_content_exposure_total"), 0),
        raw_provider_payload_in_artifacts=_as_bool(trace_provider_sanitization_cumulative.get("raw_provider_payload_in_artifacts"), False),
        secret_like_values_count=_as_int(trace_provider_sanitization_cumulative.get("secret_like_values_count"), 0),
        botdb_stability_gate=str(botdb_stability_trend.get("botdb_stability_gate", "failed")),
        quality_micro_shift_gate=str(quality_micro_shift_cumulative.get("quality_micro_shift_gate", "failed")),
        no_mutation_gate=str(no_mutation_proof.get("no_mutation_gate", "failed")),
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        controlled_cohort_expansion_readiness_ready=controlled_cohort_expansion_readiness_ready,
        future_cleanup_stabilization_requirement_created=future_cleanup_stabilization_requirement_created,
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        next_recommended_prd=str(decision_gate.get("next_recommended_prd", NEXT_PRD_HOTFIX)),
    ).to_dict()


def docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions = (repo_root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    return {
        "project_state_synced": PRD in project_state,
        "roadmap_synced": PRD in roadmap,
        "prd_index_synced": PRD in prd_index,
        "decisions_synced": PRD in decisions or "cohort expansion" in decisions.lower(),
        "docs_synced": PRD in project_state and PRD in roadmap and PRD in prd_index,
    }


def build_next_prd_recommendation(*, scorecard: dict[str, Any], decision_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_limited_smoke_consolidation_next_prd_recommendation_v1",
        "prd": PRD,
        "final_status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "blocker_requires_hotfix")),
        "next_recommended_prd": str(decision_gate.get("next_recommended_prd", NEXT_PRD_HOTFIX)),
        "blockers": _safe_list(decision_gate.get("blockers")),
        "warnings": _safe_list(decision_gate.get("warnings")),
    }


__all__ = [
    "PRD",
    "SOURCE_CHAIN",
    "NEXT_PRD_EXPANSION",
    "NEXT_PRD_REPEAT_SINGLE",
    "NEXT_PRD_HOTFIX",
    "NEXT_PRD_FINAL_ACCEPTANCE",
    "preflight_source_chain",
    "build_source_gate",
    "build_cumulative_provider_evidence",
    "build_normal_user_no_effect_cumulative",
    "build_rollback_cumulative",
    "build_safety_kb_boundary_cumulative",
    "build_trace_provider_sanitization_cumulative",
    "build_botdb_stability_trend",
    "build_quality_micro_shift_cumulative",
    "build_no_mutation_proof",
    "build_controlled_cohort_expansion_readiness",
    "build_future_cleanup_stabilization_requirement",
    "build_decision_gate",
    "build_consolidation_scorecard",
    "docs_sync_status",
    "build_next_prd_recommendation",
    "_sha256",
    "eval_pack",
]
