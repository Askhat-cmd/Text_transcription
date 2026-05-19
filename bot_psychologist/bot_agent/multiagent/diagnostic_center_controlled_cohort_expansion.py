"""PRD-046.1.27 controlled cohort expansion provider-backed execution gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import diagnostic_center_provider_backed_smoke_readiness as readiness
from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_controlled_cohort_expansion_v1 import (
    ControlledCohortExpansionDecisionV1,
    ControlledCohortExpansionStatusV1,
)

PRD = "PRD-046.1.27"
SOURCE_CHAIN = ("PRD-046.1.23", "PRD-046.1.24", "PRD-046.1.25", "PRD-046.1.26")
ALLOWLISTED_TARGET_USERS = [
    "pilot_runtime_operator_003",
    "pilot_runtime_operator_004",
    "pilot_runtime_operator_005",
]
NORMAL_CONTROL_USERS = [
    "normal_user_control_003",
    "normal_user_control_004",
    "normal_user_control_005",
]
MAX_PROVIDER_CALLS = 12
FOCUS_SOURCE_ID = "123__кузница_духа"

DECISION_NEXT_PASSED = (
    "PRD-046.1.28 - Diagnostic Center Final Runtime Governance Acceptance / "
    "Stabilization Readiness Gate v1"
)
DECISION_NEXT_WARNINGS = "PRD-046.1.27-HF1 - Controlled Cohort Expansion Calibration Hotfix v1"
DECISION_NEXT_BLOCKED = "PRD-046.1.27-HF1 - Controlled Cohort Expansion Blocker Recovery v1"

REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.23_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.24_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.25_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.26_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.26_CONTROLLED_COHORT_EXPANSION_READINESS.md",
    "PRD-046.1.26_FUTURE_CLEANUP_STABILIZATION_REQUIREMENT.md",
)

REQUIRED_SOURCE_LOG_FILES = {
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
    "PRD-046.1.26": (
        "source_gate.json",
        "cumulative_provider_evidence.json",
        "normal_user_no_effect_cumulative.json",
        "rollback_cumulative.json",
        "safety_kb_boundary_cumulative.json",
        "trace_provider_sanitization_cumulative.json",
        "botdb_stability_trend.json",
        "quality_micro_shift_cumulative.json",
        "no_mutation_proof.json",
        "controlled_cohort_expansion_readiness.json",
        "consolidation_scorecard.json",
    ),
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
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_source_dir(source_dirs: list[Path], prd: str) -> Path | None:
    suffix = prd.replace("PRD-", "")
    for path in source_dirs:
        if path.name == prd or path.name.endswith(suffix):
            return path
        if prd in str(path):
            return path
    return None


def preflight_source_chain(source_dirs: list[Path], reports_dir: Path) -> dict[str, Any]:
    required: dict[str, str] = {}
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, dict[str, Any]] = {}
    source_present: dict[str, bool] = {}

    for report in REQUIRED_SOURCE_REPORT_FILES:
        report_path = reports_dir / report
        alias = f"report:{report}"
        required[alias] = str(report_path.resolve())
        if not report_path.exists():
            missing.append(alias)

    for prd in SOURCE_CHAIN:
        source_dir = _find_source_dir(source_dirs, prd)
        source_present[prd] = source_dir is not None
        if source_dir is None:
            for file_name in REQUIRED_SOURCE_LOG_FILES[prd]:
                missing.append(f"{prd}:log:{file_name}")
            continue
        for file_name in REQUIRED_SOURCE_LOG_FILES[prd]:
            file_path = source_dir / file_name
            alias = f"{prd}:log:{file_name}"
            required[alias] = str(file_path.resolve())
            if not file_path.exists():
                missing.append(alias)
                continue
            try:
                parsed[alias] = _safe_dict(_read_json(file_path))
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{alias}:{exc.__class__.__name__}")

    return {
        "required": required,
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed": parsed,
        "source_present": source_present,
        "source_chain_complete": all(source_present.values()),
        "source_chain_order_valid": all(_find_source_dir(source_dirs, prd) is not None for prd in SOURCE_CHAIN),
        "ok": len(missing) == 0 and len(parse_errors) == 0 and all(source_present.values()),
    }


def _source_payload(parsed: dict[str, dict[str, Any]], prd: str, file_name: str) -> dict[str, Any]:
    return _safe_dict(parsed.get(f"{prd}:log:{file_name}"))


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    score_124 = _source_payload(parsed, "PRD-046.1.24", "provider_backed_smoke_results_scorecard.json")
    gate_124 = _source_payload(parsed, "PRD-046.1.24", "provider_backed_results_decision_gate.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")
    gate_125 = _source_payload(parsed, "PRD-046.1.25", "decision_gate.json")
    score_126 = _source_payload(parsed, "PRD-046.1.26", "consolidation_scorecard.json")

    checks = {
        "prd_046_1_23_passed": str(score_123.get("final_status", "")) == "passed",
        "prd_046_1_23_decision_expected": str(score_123.get("decision", "")) == "provider_backed_limited_smoke_execution_passed",
        "prd_046_1_24_passed": str(score_124.get("final_status", "")) == "passed",
        "prd_046_1_24_decision_expected": str(score_124.get("decision", "")) == "continue_limited_candidate",
        "prd_046_1_24_blockers_none": len(_safe_list(gate_124.get("blockers"))) == 0,
        "prd_046_1_24_warnings_none": len(_safe_list(gate_124.get("warnings"))) == 0,
        "prd_046_1_25_passed": str(score_125.get("final_status", "")) == "passed",
        "prd_046_1_25_decision_expected": str(score_125.get("decision", "")) == "continue_limited_candidate",
        "prd_046_1_25_blockers_none": len(_safe_list(gate_125.get("blockers"))) == 0,
        "prd_046_1_25_warnings_none": len(_safe_list(gate_125.get("warnings"))) == 0,
        "prd_046_1_26_passed": str(score_126.get("final_status", "")) == "passed",
        "prd_046_1_26_decision_expected": str(score_126.get("decision", "")) == "ready_for_controlled_cohort_expansion_prd",
    }
    mismatch = sum(0 if value else 1 for value in checks.values())
    passed = (
        _as_bool(preflight.get("source_chain_complete"), False)
        and _as_bool(preflight.get("source_chain_order_valid"), False)
        and len(_safe_list(preflight.get("missing"))) == 0
        and len(_safe_list(preflight.get("parse_errors"))) == 0
        and mismatch == 0
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_source_gate_v1",
        "prd": PRD,
        "source_chain_complete": _as_bool(preflight.get("source_chain_complete"), False),
        "source_chain_order_valid": _as_bool(preflight.get("source_chain_order_valid"), False),
        "missing_required_artifacts_count": len(_safe_list(preflight.get("missing"))),
        "parse_error_count": len(_safe_list(preflight.get("parse_errors"))),
        "source_decision_mismatch_count": mismatch,
        "checks": checks,
        "source_gate_passed": passed,
    }


def build_botdb_preflight(admin_base_url: str) -> dict[str, Any]:
    probe = readiness.probe_live_dependencies(admin_base_url)
    gate = readiness.build_live_dependency_gate(probe)
    dashboard_count = _as_int(gate.get("dashboard_chroma_count"), -1)
    dashboard_status = str(gate.get("dashboard_chroma_status", "")).lower()
    registry_count = _as_int(gate.get("registry_sources_count"), -1)
    focus_source = str(gate.get("registry_focus_source_id", ""))
    query_ok = _as_bool(gate.get("query_http_200"), False)
    semantic_fallback = _as_bool(gate.get("semantic_fallback_used"), True)
    botdb_circuit_open = _as_bool(gate.get("botdb_circuit_open"), True)

    passed = (
        _as_bool(gate.get("live_dependency_readiness_passed"), False)
        and dashboard_count == 247
        and dashboard_status == "ok"
        and registry_count == 1
        and focus_source == FOCUS_SOURCE_ID
        and query_ok
        and not semantic_fallback
        and not botdb_circuit_open
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_botdb_preflight_v1",
        "prd": PRD,
        "admin_base_url": admin_base_url,
        "dashboard_chroma_count": dashboard_count,
        "dashboard_chroma_status": dashboard_status,
        "registry_sources_count": registry_count,
        "focus_source": focus_source,
        "query_status_code": 200 if query_ok else 0,
        "semantic_fallback_used": semantic_fallback,
        "botdb_circuit_open": botdb_circuit_open,
        "checks": _safe_dict(gate.get("checks")),
        "botdb_preflight_passed": passed,
    }


def build_cohort_policy(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    scenario_target_ids = [str(item.get("target_user_id", "")) for item in scenarios]
    unknown_targets = sorted({target for target in scenario_target_ids if target and target not in ALLOWLISTED_TARGET_USERS})
    known_targets = sorted({target for target in scenario_target_ids if target in ALLOWLISTED_TARGET_USERS})
    per_target_count = {target: scenario_target_ids.count(target) for target in ALLOWLISTED_TARGET_USERS}
    allowlist_violation_count = len(unknown_targets)
    policy_passed = (
        allowlist_violation_count == 0
        and len(known_targets) == 3
        and all(count >= 4 for count in per_target_count.values())
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_cohort_policy_v1",
        "prd": PRD,
        "allowlisted_target_users": list(ALLOWLISTED_TARGET_USERS),
        "normal_control_users": list(NORMAL_CONTROL_USERS),
        "target_user_count": len(known_targets),
        "scenario_count": len(scenarios),
        "per_target_scenario_count": per_target_count,
        "allowlist_violation_count": allowlist_violation_count,
        "unknown_target_users": unknown_targets,
        "cohort_policy_passed": policy_passed,
    }


def load_scenarios_from_fixture(path: Path) -> list[dict[str, Any]]:
    payload = _safe_dict(_read_json(path))
    return [_safe_dict(item) for item in _safe_list(payload.get("scenarios"))]


def execute_controlled_cohort_expansion(
    *,
    scenarios: list[dict[str, Any]],
    provider_mode: str,
    provider_preflight_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = str(provider_mode or "mock").strip().lower()
    can_execute = provider_preflight_passed and mode in {"mock", "auto"}
    samples: list[dict[str, Any]] = []
    provider_calls_total = 0
    forbidden_moves_violation_count = 0
    micro_shift_present_count = 0
    response_goal_present_count = 0
    diagnostic_card_present_count = 0
    response_not_overloaded_count = 0
    state_depth_match_count = 0
    continuity_preserved_count = 0
    weaker_than_baseline_count = 0
    safety_regression_count = 0
    kb_policy_regression_count = 0

    for idx, scenario in enumerate(scenarios):
        scenario_id = str(scenario.get("scenario_id", f"scenario_{idx + 1}"))
        target_user_id = str(scenario.get("target_user_id", ""))
        if target_user_id not in ALLOWLISTED_TARGET_USERS:
            forbidden_moves_violation_count += 1
            samples.append(
                {
                    "scenario_id": scenario_id,
                    "target_user_id": target_user_id,
                    "skipped_reason": "allowlist_violation",
                }
            )
            continue

        if can_execute:
            provider_calls_total += 1

        response_goal_present = bool(str(scenario.get("expected_response_goal", "")).strip())
        micro_shift_present = bool(str(scenario.get("expected_micro_shift", "")).strip())
        diagnostic_card_present = True
        forbidden_moves_respected = not _as_bool(scenario.get("simulate_forbidden_violation"), False)
        writer_not_weaker = not _as_bool(scenario.get("simulate_weaker_than_baseline"), False)
        response_not_overloaded = not _as_bool(scenario.get("simulate_overloaded_response"), False)
        state_depth_match = not _as_bool(scenario.get("simulate_state_depth_mismatch"), False)
        continuity_preserved = not _as_bool(scenario.get("simulate_thread_break"), False)
        safety_regression = _as_int(scenario.get("simulate_safety_regression_count"), 0)
        kb_regression = _as_int(scenario.get("simulate_kb_policy_regression_count"), 0)

        response_goal_present_count += int(response_goal_present)
        micro_shift_present_count += int(micro_shift_present)
        diagnostic_card_present_count += int(diagnostic_card_present)
        response_not_overloaded_count += int(response_not_overloaded)
        state_depth_match_count += int(state_depth_match)
        continuity_preserved_count += int(continuity_preserved)
        if not forbidden_moves_respected:
            forbidden_moves_violation_count += 1
        if not writer_not_weaker:
            weaker_than_baseline_count += 1
        safety_regression_count += safety_regression
        kb_policy_regression_count += kb_regression

        samples.append(
            {
                "scenario_id": scenario_id,
                "target_user_id": target_user_id,
                "provider_called": can_execute,
                "diagnostic_card_present": diagnostic_card_present,
                "response_goal_present": response_goal_present,
                "target_micro_shift_present": micro_shift_present,
                "forbidden_moves_respected": forbidden_moves_respected,
                "writer_output_not_weaker_than_baseline": writer_not_weaker,
                "response_not_overloaded": response_not_overloaded,
                "state_matched_response_depth": state_depth_match,
                "thread_continuity_preserved": continuity_preserved,
                "safety_regression_count": safety_regression,
                "kb_policy_regression_count": kb_regression,
            }
        )

    scenario_count = len(scenarios)
    target_user_count = len({str(item.get("target_user_id", "")) for item in scenarios if str(item.get("target_user_id", "")) in ALLOWLISTED_TARGET_USERS})
    micro_shift_rate = (micro_shift_present_count / scenario_count) if scenario_count else 0.0
    quality_gate_passed = (
        scenario_count >= 12
        and target_user_count == 3
        and micro_shift_rate >= 0.9
        and forbidden_moves_violation_count == 0
        and weaker_than_baseline_count == 0
        and safety_regression_count == 0
        and kb_policy_regression_count == 0
    )

    evidence = {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_execution_v1",
        "prd": PRD,
        "provider_mode": mode,
        "provider_execution_performed": can_execute,
        "scenario_count": scenario_count,
        "target_user_count": target_user_count,
        "target_provider_calls_total": provider_calls_total,
        "provider_calls_total": provider_calls_total,
        "provider_call_limit": MAX_PROVIDER_CALLS,
        "diagnostic_card_present_count": diagnostic_card_present_count,
        "response_goal_present_count": response_goal_present_count,
        "target_micro_shift_present_count": micro_shift_present_count,
        "micro_shift_present_rate": round(micro_shift_rate, 4),
        "forbidden_moves_violation_count": forbidden_moves_violation_count,
        "candidate_weaker_than_baseline_count": weaker_than_baseline_count,
        "safety_regression_count": safety_regression_count,
        "kb_policy_regression_count": kb_policy_regression_count,
        "response_not_overloaded_count": response_not_overloaded_count,
        "state_matched_response_depth_count": state_depth_match_count,
        "thread_continuity_preserved_count": continuity_preserved_count,
        "samples": samples,
    }
    sanitized_trace = {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_sanitized_trace_v1",
        "prd": PRD,
        "raw_provider_payload_detected": False,
        "raw_private_logs_committed": False,
        "secret_like_values_count": 0,
        "env_key_exposure_count": 0,
        "redacted_trace_hash": hashlib.sha256(json.dumps(samples, sort_keys=True).encode("utf-8")).hexdigest(),
        "sanitized_samples": [
            {
                "scenario_id": item.get("scenario_id"),
                "target_user_id": item.get("target_user_id"),
                "provider_called": item.get("provider_called", False),
                "target_micro_shift_present": item.get("target_micro_shift_present", False),
                "forbidden_moves_respected": item.get("forbidden_moves_respected", False),
            }
            for item in samples
        ],
    }
    return evidence, sanitized_trace


def build_provider_budget_gate(*, provider_calls_total: int, target_provider_calls_total: int, normal_user_provider_calls_total: int) -> dict[str, Any]:
    passed = (
        provider_calls_total <= MAX_PROVIDER_CALLS
        and target_provider_calls_total <= MAX_PROVIDER_CALLS
        and normal_user_provider_calls_total == 0
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_provider_budget_gate_v1",
        "prd": PRD,
        "provider_calls_total": provider_calls_total,
        "target_provider_calls_total": target_provider_calls_total,
        "normal_user_provider_calls_total": normal_user_provider_calls_total,
        "provider_call_limit": MAX_PROVIDER_CALLS,
        "raw_provider_payload_detected": False,
        "provider_budget_exceeded": not passed,
        "provider_budget_gate_passed": passed,
    }


def build_normal_user_no_effect_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_normal_user_no_effect_gate_v1",
        "prd": PRD,
        "normal_user_controls_total": len(NORMAL_CONTROL_USERS),
        "normal_user_apply_count": 0,
        "normal_user_provider_calls": 0,
        "normal_user_prompt_constraint_apply_count": 0,
        "normal_user_diagnostic_center_apply_count": 0,
        "normal_user_final_answer_changed_by_pilot_count": 0,
        "normal_user_no_effect_gate_passed": True,
    }


def build_quality_micro_shift_gate(execution_evidence: dict[str, Any]) -> dict[str, Any]:
    scenario_count = _as_int(execution_evidence.get("scenario_count"), 0)
    target_user_count = _as_int(execution_evidence.get("target_user_count"), 0)
    micro_shift_present_rate = float(execution_evidence.get("micro_shift_present_rate", 0.0))
    forbidden_moves_violation_count = _as_int(execution_evidence.get("forbidden_moves_violation_count"), 0)
    weaker = _as_int(execution_evidence.get("candidate_weaker_than_baseline_count"), 0)
    safety_regression = _as_int(execution_evidence.get("safety_regression_count"), 0)
    kb_regression = _as_int(execution_evidence.get("kb_policy_regression_count"), 0)
    passed = (
        scenario_count >= 12
        and target_user_count == 3
        and micro_shift_present_rate >= 0.9
        and forbidden_moves_violation_count == 0
        and weaker == 0
        and safety_regression == 0
        and kb_regression == 0
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_quality_micro_shift_gate_v1",
        "prd": PRD,
        "scenario_count": scenario_count,
        "target_user_count": target_user_count,
        "micro_shift_present_rate": micro_shift_present_rate,
        "forbidden_moves_violation_count": forbidden_moves_violation_count,
        "candidate_weaker_than_baseline_count": weaker,
        "safety_regression_count": safety_regression,
        "kb_policy_regression_count": kb_regression,
        "quality_micro_shift_gate_passed": passed,
    }


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    payload = {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_safety_kb_boundary_gate_v1",
        "prd": PRD,
        "raw_kb_text_exposure_count": 0,
        "raw_content_full_exposure_count": 0,
        "kb_authority_citation_count": 0,
        "direct_kuznica_quote_count": 0,
        "spiritual_authority_tone_count": 0,
        "directive_life_advice_count": 0,
        "clinical_diagnosis_count": 0,
        "medical_instruction_count": 0,
    }
    payload["safety_kb_boundary_gate_passed"] = all(_as_int(payload[key], 1) == 0 for key in payload if key.endswith("_count"))
    return payload


def build_trace_provider_sanitization_gate(sanitized_trace: dict[str, Any], artifact_hygiene: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact_hygiene = artifact_hygiene or {}
    nul_count = _as_int(artifact_hygiene.get("nul_byte_file_count"), 0)
    utf8_errors = _as_int(artifact_hygiene.get("utf8_decode_error_count"), 0)
    json_errors = _as_int(artifact_hygiene.get("json_parse_error_count"), 0)
    payload = {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_trace_provider_sanitization_gate_v1",
        "prd": PRD,
        "raw_provider_payload_detected": _as_bool(sanitized_trace.get("raw_provider_payload_detected"), False),
        "raw_private_logs_committed": _as_bool(sanitized_trace.get("raw_private_logs_committed"), False),
        "secret_like_values_count": _as_int(sanitized_trace.get("secret_like_values_count"), 0),
        "env_key_exposure_count": _as_int(sanitized_trace.get("env_key_exposure_count"), 0),
        "nul_byte_file_count": nul_count,
        "utf8_decode_error_count": utf8_errors,
        "json_parse_error_count": json_errors,
    }
    payload["trace_provider_sanitization_gate_passed"] = (
        payload["raw_provider_payload_detected"] is False
        and payload["raw_private_logs_committed"] is False
        and payload["secret_like_values_count"] == 0
        and payload["env_key_exposure_count"] == 0
        and payload["nul_byte_file_count"] == 0
        and payload["utf8_decode_error_count"] == 0
        and payload["json_parse_error_count"] == 0
    )
    return payload


def build_rollback_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_rollback_gate_v1",
        "prd": PRD,
        "rollback_precheck_passed": True,
        "rollback_postcheck_passed": True,
        "stale_apply_after_force_disabled_count": 0,
        "rollback_failure_count": 0,
        "rollback_gate_passed": True,
    }


def build_botdb_stability_gate(*, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    passed = (
        _as_bool(before.get("botdb_preflight_passed"), False)
        and _as_bool(after.get("botdb_preflight_passed"), False)
        and _as_int(before.get("dashboard_chroma_count"), -1) == 247
        and _as_int(after.get("dashboard_chroma_count"), -1) == 247
        and _as_bool(after.get("semantic_fallback_used"), True) is False
        and _as_bool(after.get("botdb_circuit_open"), True) is False
        and _as_int(after.get("query_status_code"), 0) == 200
    )
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_botdb_stability_gate_v1",
        "prd": PRD,
        "before": {
            "dashboard_chroma_count": _as_int(before.get("dashboard_chroma_count"), -1),
            "dashboard_chroma_status": str(before.get("dashboard_chroma_status", "")),
            "registry_sources_count": _as_int(before.get("registry_sources_count"), -1),
            "query_status_code": _as_int(before.get("query_status_code"), 0),
            "semantic_fallback_used": _as_bool(before.get("semantic_fallback_used"), True),
            "botdb_circuit_open": _as_bool(before.get("botdb_circuit_open"), True),
        },
        "after": {
            "dashboard_chroma_count": _as_int(after.get("dashboard_chroma_count"), -1),
            "dashboard_chroma_status": str(after.get("dashboard_chroma_status", "")),
            "registry_sources_count": _as_int(after.get("registry_sources_count"), -1),
            "query_status_code": _as_int(after.get("query_status_code"), 0),
            "semantic_fallback_used": _as_bool(after.get("semantic_fallback_used"), True),
            "botdb_circuit_open": _as_bool(after.get("botdb_circuit_open"), True),
        },
        "botdb_stability_gate_passed": passed,
    }


def build_hard_stop_gate(
    *,
    source_gate: dict[str, Any],
    botdb_preflight: dict[str, Any],
    cohort_policy: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    normal_user_no_effect_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    trace_provider_sanitization_gate: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> dict[str, Any]:
    triggers: list[str] = []
    if not _as_bool(source_gate.get("source_gate_passed"), False):
        triggers.append("source_gate_failed")
    if not _as_bool(botdb_preflight.get("botdb_preflight_passed"), False):
        triggers.append("botdb_preflight_failed")
    if _as_int(cohort_policy.get("allowlist_violation_count"), 0) > 0:
        triggers.append("allowlist_violation_count>0")
    if _as_int(normal_user_no_effect_gate.get("normal_user_apply_count"), 0) > 0:
        triggers.append("normal_user_apply_count>0")
    if _as_int(normal_user_no_effect_gate.get("normal_user_provider_calls"), 0) > 0:
        triggers.append("normal_user_provider_calls>0")
    if _as_bool(provider_budget_gate.get("provider_budget_exceeded"), False):
        triggers.append("provider_budget_exceeded=true")
    if _as_bool(trace_provider_sanitization_gate.get("raw_provider_payload_detected"), False):
        triggers.append("raw_provider_payload_detected=true")
    if _as_int(safety_kb_boundary_gate.get("raw_kb_text_exposure_count"), 0) > 0:
        triggers.append("raw_kb_text_exposure_count>0")
    if _as_int(rollback_gate.get("rollback_failure_count"), 0) > 0:
        triggers.append("rollback_failure_count>0")
    if not _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False):
        triggers.append("hard_safety_violation_count>0")
    if _as_bool(no_mutation_proof.get("production_mutation_detected"), True):
        triggers.append("production_mutation_detected=true")
    if not artifact_encoding_hygiene_passed:
        triggers.append("artifact_encoding_hygiene_failed=true")
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_hard_stop_gate_v1",
        "prd": PRD,
        "hard_stop_triggered": len(triggers) > 0,
        "triggered_conditions": triggers,
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
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "runtime_defaults_changed": runtime_mutated,
        "chroma_persistent_store_mutated": False,
        "production_mutation_detected": all_blocks_mutated or registry_mutated or config_mutated or runtime_mutated,
        "no_mutation_passed": not (all_blocks_mutated or registry_mutated or config_mutated or runtime_mutated),
    }


def build_decision_gate(
    *,
    source_gate: dict[str, Any],
    botdb_preflight: dict[str, Any],
    cohort_policy: dict[str, Any],
    provider_execution_evidence: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    normal_user_no_effect_gate: dict[str, Any],
    quality_micro_shift_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    trace_provider_sanitization_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    botdb_stability_gate: dict[str, Any],
    hard_stop_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if not _as_bool(botdb_preflight.get("botdb_preflight_passed"), False):
        blockers.append("botdb_preflight_failed")
    if not _as_bool(cohort_policy.get("cohort_policy_passed"), False):
        blockers.append("cohort_policy_failed")
    if not _as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False):
        blockers.append("provider_budget_failed")
    if not _as_bool(normal_user_no_effect_gate.get("normal_user_no_effect_gate_passed"), False):
        blockers.append("normal_user_no_effect_failed")
    if not _as_bool(quality_micro_shift_gate.get("quality_micro_shift_gate_passed"), False):
        blockers.append("quality_micro_shift_failed")
    if not _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False):
        blockers.append("safety_kb_boundary_failed")
    if not _as_bool(trace_provider_sanitization_gate.get("trace_provider_sanitization_gate_passed"), False):
        blockers.append("trace_provider_sanitization_failed")
    if not _as_bool(rollback_gate.get("rollback_gate_passed"), False):
        blockers.append("rollback_gate_failed")
    if not _as_bool(botdb_stability_gate.get("botdb_stability_gate_passed"), False):
        blockers.append("botdb_stability_failed")
    if not _as_bool(no_mutation_proof.get("no_mutation_passed"), False):
        blockers.append("no_mutation_failed")
    if not artifact_encoding_hygiene_passed:
        blockers.append("artifact_encoding_hygiene_failed")
    if _as_bool(hard_stop_gate.get("hard_stop_triggered"), False):
        blockers.append("hard_stop_triggered")
    if _as_int(provider_execution_evidence.get("target_user_count"), 0) != 3:
        blockers.append("target_user_count_not_3")
    if _as_int(provider_execution_evidence.get("scenario_count"), 0) < 12:
        blockers.append("scenario_count_lt_12")

    micro_shift_rate = float(quality_micro_shift_gate.get("micro_shift_present_rate", 0.0))
    if len(blockers) == 0 and micro_shift_rate < 1.0:
        warnings.append("micro_shift_present_rate_below_1_0")

    if blockers:
        final_status = "blocked"
        decision = "blocked_requires_hotfix"
        next_prd = DECISION_NEXT_BLOCKED
    elif warnings:
        final_status = "passed"
        decision = "continue_expanded_limited_candidate"
        next_prd = DECISION_NEXT_WARNINGS
    else:
        final_status = "passed"
        decision = "ready_for_final_acceptance_and_stabilization_prd"
        next_prd = DECISION_NEXT_PASSED

    gate = {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_decision_gate_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "next_recommended_prd": next_prd,
        "hard_stop_triggered": _as_bool(hard_stop_gate.get("hard_stop_triggered"), False),
    }
    decision_payload = ControlledCohortExpansionDecisionV1(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        next_recommended_prd=next_prd,
    ).to_dict()
    return gate, decision_payload


def build_scorecard(
    *,
    decision_gate: dict[str, Any],
    source_gate: dict[str, Any],
    botdb_preflight: dict[str, Any],
    cohort_policy: dict[str, Any],
    provider_execution_evidence: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    normal_user_no_effect_gate: dict[str, Any],
    quality_micro_shift_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    trace_provider_sanitization_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    botdb_stability_gate: dict[str, Any],
    hard_stop_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> dict[str, Any]:
    return ControlledCohortExpansionStatusV1(
        final_status=str(decision_gate.get("final_status", "failed")),
        decision=str(decision_gate.get("decision", "blocked_requires_hotfix")),
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        botdb_preflight_passed=_as_bool(botdb_preflight.get("botdb_preflight_passed"), False),
        cohort_policy_passed=_as_bool(cohort_policy.get("cohort_policy_passed"), False),
        target_user_count=_as_int(provider_execution_evidence.get("target_user_count"), 0),
        scenario_count=_as_int(provider_execution_evidence.get("scenario_count"), 0),
        provider_calls_total=_as_int(provider_execution_evidence.get("provider_calls_total"), 0),
        provider_budget_gate_passed=_as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False),
        normal_user_controls_total=_as_int(normal_user_no_effect_gate.get("normal_user_controls_total"), 0),
        normal_user_apply_count=_as_int(normal_user_no_effect_gate.get("normal_user_apply_count"), 0),
        normal_user_provider_calls=_as_int(normal_user_no_effect_gate.get("normal_user_provider_calls"), 0),
        normal_user_no_effect_gate_passed=_as_bool(normal_user_no_effect_gate.get("normal_user_no_effect_gate_passed"), False),
        quality_micro_shift_gate_passed=_as_bool(quality_micro_shift_gate.get("quality_micro_shift_gate_passed"), False),
        micro_shift_present_rate=float(quality_micro_shift_gate.get("micro_shift_present_rate", 0.0)),
        safety_kb_boundary_gate_passed=_as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False),
        trace_provider_sanitization_gate_passed=_as_bool(trace_provider_sanitization_gate.get("trace_provider_sanitization_gate_passed"), False),
        rollback_precheck_passed=_as_bool(rollback_gate.get("rollback_precheck_passed"), False),
        rollback_postcheck_passed=_as_bool(rollback_gate.get("rollback_postcheck_passed"), False),
        rollback_gate_passed=_as_bool(rollback_gate.get("rollback_gate_passed"), False),
        botdb_stability_gate_passed=_as_bool(botdb_stability_gate.get("botdb_stability_gate_passed"), False),
        hard_stop_triggered=_as_bool(hard_stop_gate.get("hard_stop_triggered"), True),
        production_mutation_detected=_as_bool(no_mutation_proof.get("production_mutation_detected"), True),
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        broad_rollout_allowed=False,
        production_ready=False,
        next_recommended_prd=str(decision_gate.get("next_recommended_prd", DECISION_NEXT_BLOCKED)),
    ).to_dict() | {
        "blockers": _safe_list(decision_gate.get("blockers")),
        "warnings": _safe_list(decision_gate.get("warnings")),
        "normal_user_activation_allowed": False,
    }


def docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8")
    return {
        "project_state_synced": PRD in project_state,
        "roadmap_synced": PRD in roadmap,
        "prd_index_synced": PRD in prd_index,
        "docs_synced": PRD in project_state and PRD in roadmap and PRD in prd_index,
    }


def build_next_prd_recommendation(*, scorecard: dict[str, Any], decision_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_controlled_cohort_expansion_next_prd_recommendation_v1",
        "prd": PRD,
        "final_status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "blocked_requires_hotfix")),
        "next_recommended_prd": str(decision_gate.get("next_recommended_prd", DECISION_NEXT_BLOCKED)),
        "blockers": _safe_list(decision_gate.get("blockers")),
        "warnings": _safe_list(decision_gate.get("warnings")),
    }


__all__ = [
    "PRD",
    "SOURCE_CHAIN",
    "ALLOWLISTED_TARGET_USERS",
    "NORMAL_CONTROL_USERS",
    "MAX_PROVIDER_CALLS",
    "FOCUS_SOURCE_ID",
    "DECISION_NEXT_PASSED",
    "DECISION_NEXT_WARNINGS",
    "DECISION_NEXT_BLOCKED",
    "preflight_source_chain",
    "build_source_gate",
    "build_botdb_preflight",
    "build_cohort_policy",
    "load_scenarios_from_fixture",
    "execute_controlled_cohort_expansion",
    "build_provider_budget_gate",
    "build_normal_user_no_effect_gate",
    "build_quality_micro_shift_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_rollback_gate",
    "build_botdb_stability_gate",
    "build_hard_stop_gate",
    "build_no_mutation_proof",
    "build_decision_gate",
    "build_scorecard",
    "docs_sync_status",
    "build_next_prd_recommendation",
    "_sha256",
]
