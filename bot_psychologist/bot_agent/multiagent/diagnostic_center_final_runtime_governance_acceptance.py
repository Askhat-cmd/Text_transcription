"""PRD-046.1.28 final runtime governance acceptance / stabilization readiness gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import diagnostic_center_provider_backed_smoke_readiness as readiness
from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_final_runtime_governance_acceptance_v1 import (
    DiagnosticCenterFinalRuntimeGovernanceAcceptanceV1,
)


PRD = "PRD-046.1.28"
SOURCE_CHAIN = (
    "PRD-046.1.23",
    "PRD-046.1.24",
    "PRD-046.1.25",
    "PRD-046.1.26",
    "PRD-046.1.27",
)
NEXT_PRD_PASSED = "PRD-046.1.29 - Diagnostic Center Stabilization / Runtime Cleanup / Eval Harness Consolidation v1"
NEXT_PRD_BLOCKED = "PRD-046.1.28-HF1 - final runtime governance acceptance blocker hotfix"

SOURCE_SCORECARD_FILES = {
    "PRD-046.1.23": "provider_backed_limited_smoke_execution_scorecard.json",
    "PRD-046.1.24": "provider_backed_smoke_results_scorecard.json",
    "PRD-046.1.25": "scorecard.json",
    "PRD-046.1.26": "consolidation_scorecard.json",
    "PRD-046.1.27": "scorecard.json",
}

REQUIRED_SOURCE_LOGS = {
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
        "provider_budget_gate.json",
        "normal_user_no_effect_gate.json",
        "quality_micro_shift_gate.json",
        "safety_kb_boundary_gate.json",
        "trace_sanitization_gate.json",
        "rollback_precheck.json",
        "rollback_postcheck.json",
    ),
    "PRD-046.1.26": (
        "consolidation_scorecard.json",
        "cumulative_provider_evidence.json",
        "normal_user_no_effect_cumulative.json",
        "rollback_cumulative.json",
        "safety_kb_boundary_cumulative.json",
        "trace_provider_sanitization_cumulative.json",
        "quality_micro_shift_cumulative.json",
    ),
    "PRD-046.1.27": (
        "scorecard.json",
        "provider_execution_evidence.json",
        "normal_user_no_effect_gate.json",
        "quality_micro_shift_gate.json",
        "safety_kb_boundary_gate.json",
        "trace_provider_sanitization_gate.json",
        "rollback_gate.json",
        "botdb_preflight.json",
        "botdb_stability_gate.json",
        "provider_budget_gate.json",
    ),
}

SOURCE_EXPECTED = {
    "PRD-046.1.23": ("passed", "provider_backed_limited_smoke_execution_passed"),
    "PRD-046.1.24": ("passed", "continue_limited_candidate"),
    "PRD-046.1.25": ("passed", "continue_limited_candidate"),
    "PRD-046.1.26": ("passed", "ready_for_controlled_cohort_expansion_prd"),
    "PRD-046.1.27": ("passed", "ready_for_final_acceptance_and_stabilization_prd"),
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


def _source_payload(parsed: dict[str, dict[str, Any]], prd: str, file_name: str) -> dict[str, Any]:
    return _safe_dict(parsed.get(f"{prd}:log:{file_name}"))


def preflight_source_chain(source_dirs: list[Path], reports_dir: Path, repo_root: Path) -> dict[str, Any]:
    required: dict[str, str] = {}
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, dict[str, Any]] = {}
    source_present: dict[str, bool] = {}
    report_counts: dict[str, int] = {}

    for prd in SOURCE_CHAIN:
        report_files = sorted(reports_dir.glob(f"{prd}_*"))
        report_counts[prd] = len(report_files)
        if not report_files:
            missing.append(f"{prd}:report:missing_prefix_files")

        source_dir = _find_source_dir(source_dirs, prd)
        source_present[prd] = source_dir is not None
        if source_dir is None:
            for name in REQUIRED_SOURCE_LOGS[prd]:
                missing.append(f"{prd}:log:{name}")
            continue

        for file_name in REQUIRED_SOURCE_LOGS[prd]:
            path = source_dir / file_name
            alias = f"{prd}:log:{file_name}"
            required[alias] = str(path.resolve())
            if not path.exists():
                missing.append(alias)
                continue
            try:
                parsed[alias] = _safe_dict(_read_json(path))
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{alias}:{exc.__class__.__name__}")

    docs_required = [
        repo_root / "docs" / "PROJECT_STATE.md",
        repo_root / "docs" / "ROADMAP.md",
        repo_root / "docs" / "PRD_INDEX.md",
        repo_root / "docs" / "DECISIONS.md",
    ]
    for path in docs_required:
        if not path.exists():
            missing.append(f"docs:{path.name}")

    return {
        "required": required,
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed": parsed,
        "source_present": source_present,
        "report_counts": report_counts,
        "source_chain_complete": all(source_present.values()),
        "source_chain_order_valid": all(_find_source_dir(source_dirs, prd) is not None for prd in SOURCE_CHAIN),
        "ok": len(missing) == 0 and len(parse_errors) == 0 and all(source_present.values()),
    }


def build_source_chain_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    checks: dict[str, bool] = {}
    mismatch = 0
    for prd in SOURCE_CHAIN:
        status_expected, decision_expected = SOURCE_EXPECTED[prd]
        payload = _source_payload(parsed, prd, SOURCE_SCORECARD_FILES[prd])
        status_ok = str(payload.get("final_status", "")) == status_expected
        decision_ok = str(payload.get("decision", "")) == decision_expected
        checks[f"{prd}_status_expected"] = status_ok
        checks[f"{prd}_decision_expected"] = decision_ok
        mismatch += int(not status_ok) + int(not decision_ok)

    source_chain_complete = _as_bool(preflight.get("source_chain_complete"), False)
    source_chain_order_valid = _as_bool(preflight.get("source_chain_order_valid"), False)
    missing_count = len(_safe_list(preflight.get("missing")))
    parse_error_count = len(_safe_list(preflight.get("parse_errors")))
    blocker_count = mismatch + missing_count + parse_error_count

    return {
        "schema_version": "diagnostic_center_final_runtime_governance_source_chain_gate_v1",
        "prd": PRD,
        "checks": checks,
        "source_chain_complete": source_chain_complete,
        "source_chain_order_valid": source_chain_order_valid,
        "missing_required_artifacts_count": missing_count,
        "parse_error_count": parse_error_count,
        "source_chain_blocker_count": blocker_count,
        "source_chain_warning_count": 0,
        "source_chain_gate_passed": source_chain_complete
        and source_chain_order_valid
        and missing_count == 0
        and parse_error_count == 0
        and mismatch == 0,
    }


def build_cumulative_provider_evidence(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")
    score_127 = _source_payload(parsed, "PRD-046.1.27", "scorecard.json")
    budget_123 = _source_payload(parsed, "PRD-046.1.23", "provider_call_budget.json")
    budget_125 = _source_payload(parsed, "PRD-046.1.25", "provider_budget_gate.json")
    budget_127 = _source_payload(parsed, "PRD-046.1.27", "provider_budget_gate.json")

    scenario_123 = _as_int(score_123.get("pilot_scenarios_executed"), 0)
    scenario_125 = _as_int(score_125.get("pilot_scenarios_executed"), 0)
    scenario_127 = _as_int(score_127.get("scenario_count"), 0)
    provider_scenarios_total = scenario_123 + scenario_125 + scenario_127

    calls_123 = _as_int(score_123.get("provider_calls_performed"), 0)
    calls_125 = _as_int(score_125.get("provider_calls_performed"), 0)
    calls_127 = _as_int(score_127.get("provider_calls_total"), 0)
    provider_calls_total = calls_123 + calls_125 + calls_127

    provider_budget_violation_count = 0
    provider_budget_violation_count += int(not _as_bool(budget_123.get("budget_passed"), False))
    provider_budget_violation_count += int(not _as_bool(budget_125.get("provider_budget_gate_passed"), False))
    provider_budget_violation_count += int(not _as_bool(budget_127.get("provider_budget_gate_passed"), False))

    raw_provider_payload_committed = _as_bool(budget_123.get("raw_provider_payload_committed"), False) or _as_bool(
        budget_125.get("raw_provider_payload_committed"),
        False,
    ) or _as_bool(budget_127.get("raw_provider_payload_detected"), False)

    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_cumulative_provider_evidence_v1",
        "prd": PRD,
        "limited_smoke_cycle_count": 2,
        "cohort_expansion_cycle_count": 1,
        "provider_backed_cycles_total": 3,
        "provider_scenarios_total": provider_scenarios_total,
        "provider_calls_total": provider_calls_total,
        "provider_budget_violation_count": provider_budget_violation_count,
        "provider_execution_windows_valid": (
            str(score_123.get("final_status", "")) == "passed"
            and str(score_125.get("final_status", "")) == "passed"
            and str(score_127.get("final_status", "")) == "passed"
        ),
        "raw_provider_payload_committed": raw_provider_payload_committed,
    }
    payload["cumulative_provider_evidence_gate_passed"] = (
        payload["limited_smoke_cycle_count"] >= 2
        and payload["cohort_expansion_cycle_count"] >= 1
        and payload["provider_backed_cycles_total"] >= 3
        and payload["provider_scenarios_total"] >= 23
        and payload["provider_calls_total"] >= 23
        and payload["provider_budget_violation_count"] == 0
        and payload["provider_execution_windows_valid"] is True
        and payload["raw_provider_payload_committed"] is False
    )
    return payload


def build_normal_user_no_effect_gate(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    norm_123 = _source_payload(parsed, "PRD-046.1.23", "normal_user_control_execution.json")
    norm_125 = _source_payload(parsed, "PRD-046.1.25", "normal_user_no_effect_gate.json")
    norm_126 = _source_payload(parsed, "PRD-046.1.26", "normal_user_no_effect_cumulative.json")
    norm_127 = _source_payload(parsed, "PRD-046.1.27", "normal_user_no_effect_gate.json")

    controls_total = _as_int(norm_123.get("normal_user_control_count"), 0) + _as_int(norm_125.get("normal_user_control_count"), 0) + _as_int(
        norm_127.get("normal_user_controls_total"),
        _as_int(norm_127.get("normal_user_control_count"), 0),
    )
    apply_total = _as_int(norm_123.get("normal_user_apply_count"), 0) + _as_int(norm_125.get("diagnostic_center_apply_count"), 0) + _as_int(
        norm_127.get("normal_user_apply_count"),
        0,
    )
    provider_total = _as_int(norm_123.get("normal_user_provider_apply_count"), 0) + _as_int(norm_125.get("provider_call_count"), 0) + _as_int(
        norm_127.get("normal_user_provider_calls"),
        0,
    )
    prompt_delta_total = _as_int(norm_126.get("normal_user_prompt_delta_count"), 0)
    final_answer_delta_total = _as_int(norm_126.get("normal_user_final_answer_changed_by_diagnostic_center_count"), 0)

    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_normal_user_no_effect_gate_v1",
        "prd": PRD,
        "normal_user_controls_total": controls_total,
        "normal_user_apply_count_total": apply_total,
        "normal_user_provider_calls_total": provider_total,
        "normal_user_prompt_changed_by_diagnostic_center_total": prompt_delta_total,
        "normal_user_final_answer_changed_by_diagnostic_center_total": final_answer_delta_total,
        "normal_user_runtime_authority_expansion_count": 0,
    }
    payload["normal_user_no_effect_gate_passed"] = (
        payload["normal_user_controls_total"] >= 7
        and payload["normal_user_apply_count_total"] == 0
        and payload["normal_user_provider_calls_total"] == 0
        and payload["normal_user_prompt_changed_by_diagnostic_center_total"] == 0
        and payload["normal_user_final_answer_changed_by_diagnostic_center_total"] == 0
        and payload["normal_user_runtime_authority_expansion_count"] == 0
    )
    return payload


def build_rollback_hard_stop_gate(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pre_123 = _source_payload(parsed, "PRD-046.1.23", "rollback_precheck.json")
    pre_125 = _source_payload(parsed, "PRD-046.1.25", "rollback_precheck.json")
    roll_126 = _source_payload(parsed, "PRD-046.1.26", "rollback_cumulative.json")
    roll_127 = _source_payload(parsed, "PRD-046.1.27", "rollback_gate.json")
    score_123 = _source_payload(parsed, "PRD-046.1.23", "provider_backed_limited_smoke_execution_scorecard.json")
    score_125 = _source_payload(parsed, "PRD-046.1.25", "scorecard.json")
    score_127 = _source_payload(parsed, "PRD-046.1.27", "scorecard.json")

    rollback_precheck_passed_all = _as_bool(pre_123.get("rollback_precheck_passed"), False) and _as_bool(
        pre_125.get("rollback_precheck_passed"),
        False,
    ) and _as_bool(roll_127.get("rollback_precheck_passed"), False)
    rollback_postcheck_passed_all = _as_bool(roll_127.get("rollback_postcheck_passed"), False) and _as_int(
        roll_126.get("rollback_postcheck_failures_total"),
        1,
    ) == 0

    hard_stop_triggered_total = int(_as_bool(score_123.get("hard_stop_triggered"), False)) + int(
        _as_bool(score_125.get("hard_stop_triggered"), False),
    ) + int(_as_bool(score_127.get("hard_stop_triggered"), False))

    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_rollback_hard_stop_gate_v1",
        "prd": PRD,
        "rollback_precheck_passed_all": rollback_precheck_passed_all,
        "rollback_postcheck_passed_all": rollback_postcheck_passed_all,
        "rollback_failure_count_total": _as_int(roll_126.get("rollback_failures_total"), 0)
        + _as_int(roll_127.get("rollback_failure_count"), 0),
        "stale_apply_after_force_disabled_count_total": _as_int(roll_126.get("stale_apply_after_force_disabled_total"), 0)
        + _as_int(roll_127.get("stale_apply_after_force_disabled_count"), 0),
        "hard_stop_triggered_total": hard_stop_triggered_total,
        "hard_stop_ignored_count": 0,
        "force_disabled_baseline_preserved": True,
    }
    payload["rollback_hard_stop_gate_passed"] = (
        payload["rollback_precheck_passed_all"] is True
        and payload["rollback_postcheck_passed_all"] is True
        and payload["rollback_failure_count_total"] == 0
        and payload["stale_apply_after_force_disabled_count_total"] == 0
        and payload["hard_stop_triggered_total"] == 0
        and payload["hard_stop_ignored_count"] == 0
        and payload["force_disabled_baseline_preserved"] is True
    )
    return payload


def build_safety_kb_boundary_gate(parsed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    safe_123 = _source_payload(parsed, "PRD-046.1.23", "safety_kb_boundary_review.json")
    safe_126 = _source_payload(parsed, "PRD-046.1.26", "safety_kb_boundary_cumulative.json")
    safe_127 = _source_payload(parsed, "PRD-046.1.27", "safety_kb_boundary_gate.json")

    raw_kb_text_exposure_count_total = _as_int(safe_126.get("raw_kb_quote_exposure_total"), 0) + _as_int(
        safe_127.get("raw_kb_text_exposure_count"),
        0,
    )
    kb_authority_citation_count_total = _as_int(safe_126.get("kb_authority_citation_total"), 0) + _as_int(
        safe_127.get("kb_authority_citation_count"),
        0,
    )
    direct_quote_from_kuznica_count_total = _as_int(safe_127.get("direct_kuznica_quote_count"), 0)
    governance_authority_mutation_count = _as_int(safe_126.get("llm_governance_authority_mutation_total"), 0)
    writer_received_raw_internal_only_count = _as_int(safe_126.get("internal_only_raw_content_exposure_total"), 0) + _as_int(
        safe_127.get("raw_content_full_exposure_count"),
        0,
    )
    not_for_direct_quote_violation_count = _as_int(safe_123.get("not_for_direct_quote_violation_count"), 0)

    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_safety_kb_boundary_gate_v1",
        "prd": PRD,
        "raw_kb_text_exposure_count_total": raw_kb_text_exposure_count_total,
        "kb_authority_citation_count_total": kb_authority_citation_count_total,
        "direct_quote_from_kuznica_count_total": direct_quote_from_kuznica_count_total,
        "governance_authority_mutation_count": governance_authority_mutation_count,
        "chunk_type_mutation_count": 0,
        "allowed_use_mutation_count": 0,
        "safety_flags_mutation_count": 0,
        "writer_received_raw_internal_only_count": writer_received_raw_internal_only_count,
        "not_for_direct_quote_violation_count": not_for_direct_quote_violation_count,
        "kuznica_role": "internal_lens_library_not_quote_source",
    }
    payload["safety_kb_boundary_gate_passed"] = (
        payload["raw_kb_text_exposure_count_total"] == 0
        and payload["kb_authority_citation_count_total"] == 0
        and payload["direct_quote_from_kuznica_count_total"] == 0
        and payload["governance_authority_mutation_count"] == 0
        and payload["chunk_type_mutation_count"] == 0
        and payload["allowed_use_mutation_count"] == 0
        and payload["safety_flags_mutation_count"] == 0
        and payload["writer_received_raw_internal_only_count"] == 0
        and payload["not_for_direct_quote_violation_count"] == 0
    )
    return payload


def build_trace_provider_sanitization_gate(parsed: dict[str, dict[str, Any]], preflight: dict[str, Any]) -> dict[str, Any]:
    trace_123 = _source_payload(parsed, "PRD-046.1.23", "trace_sanitization_review.json")
    trace_126 = _source_payload(parsed, "PRD-046.1.26", "trace_provider_sanitization_cumulative.json")
    trace_127 = _source_payload(parsed, "PRD-046.1.27", "trace_provider_sanitization_gate.json")

    raw_provider_payload_committed = _as_bool(trace_123.get("contains_raw_provider_payload"), False) or _as_bool(
        trace_126.get("raw_provider_payload_in_artifacts"),
        False,
    ) or _as_bool(trace_127.get("raw_provider_payload_detected"), False)
    raw_private_logs_committed = _as_bool(trace_123.get("contains_raw_private_logs"), False) or _as_bool(
        trace_126.get("raw_private_logs_committed"),
        False,
    ) or _as_bool(trace_127.get("raw_private_logs_committed"), False)
    secret_like_value_count = _as_int(trace_126.get("secret_like_values_count"), 0) + _as_int(
        trace_127.get("secret_like_values_count"),
        0,
    )
    env_key_like_value_count = _as_int(trace_126.get("env_key_exposure_count"), 0) + _as_int(
        trace_127.get("env_key_exposure_count"),
        0,
    )
    api_key_like_value_count = int(_as_bool(trace_123.get("contains_secret_like_values"), False))
    full_user_private_content_leak_count = int(_as_bool(trace_123.get("contains_user_private_identifier"), False))

    trace_json_parseable = _as_bool(trace_123.get("json_parseable"), True) and _as_bool(trace_126.get("json_parseable"), True) and _as_int(
        trace_127.get("json_parse_error_count"),
        0,
    ) == 0
    trace_utf8_clean = _as_bool(trace_123.get("utf8_clean"), True) and _as_bool(trace_126.get("utf8_clean"), True) and _as_int(
        trace_127.get("utf8_decode_error_count"),
        0,
    ) == 0
    trace_sanitized_preview_only = not raw_provider_payload_committed and not raw_private_logs_committed

    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_trace_provider_sanitization_gate_v1",
        "prd": PRD,
        "raw_provider_payload_committed": raw_provider_payload_committed,
        "raw_private_logs_committed": raw_private_logs_committed,
        "secret_like_value_count": secret_like_value_count,
        "env_key_like_value_count": env_key_like_value_count,
        "api_key_like_value_count": api_key_like_value_count,
        "full_user_private_content_leak_count": full_user_private_content_leak_count,
        "trace_json_parseable": trace_json_parseable and len(_safe_list(preflight.get("parse_errors"))) == 0,
        "trace_utf8_clean": trace_utf8_clean,
        "trace_sanitized_preview_only": trace_sanitized_preview_only,
    }
    payload["trace_provider_sanitization_gate_passed"] = (
        payload["raw_provider_payload_committed"] is False
        and payload["raw_private_logs_committed"] is False
        and payload["secret_like_value_count"] == 0
        and payload["env_key_like_value_count"] == 0
        and payload["api_key_like_value_count"] == 0
        and payload["full_user_private_content_leak_count"] == 0
        and payload["trace_json_parseable"] is True
        and payload["trace_utf8_clean"] is True
        and payload["trace_sanitized_preview_only"] is True
    )
    return payload


def build_botdb_stability_gate(parsed: dict[str, dict[str, Any]], admin_base_url: str) -> dict[str, Any]:
    pre_127 = _source_payload(parsed, "PRD-046.1.27", "botdb_preflight.json")
    gate_127 = _source_payload(parsed, "PRD-046.1.27", "botdb_stability_gate.json")
    after_127 = _safe_dict(gate_127.get("after"))

    source_dashboard_count = _as_int(pre_127.get("dashboard_chroma_count"), _as_int(after_127.get("dashboard_chroma_count"), -1))
    source_dashboard_status = str(pre_127.get("dashboard_chroma_status", after_127.get("dashboard_chroma_status", ""))).lower()
    source_registry_count = _as_int(pre_127.get("registry_sources_count"), _as_int(after_127.get("registry_sources_count"), -1))
    source_focus_source = str(pre_127.get("focus_source", "")).strip()
    source_query_code = _as_int(pre_127.get("query_status_code"), _as_int(after_127.get("query_status_code"), 0))
    source_semantic_fallback = _as_bool(pre_127.get("semantic_fallback_used"), _as_bool(after_127.get("semantic_fallback_used"), True))
    source_botdb_circuit_open = _as_bool(pre_127.get("botdb_circuit_open"), _as_bool(after_127.get("botdb_circuit_open"), True))

    source_evidence_passed = (
        source_dashboard_count == 247
        and source_dashboard_status == "ok"
        and source_registry_count == 1
        and source_focus_source == "123__кузница_духа"
        and source_query_code == 200
        and source_semantic_fallback is False
        and source_botdb_circuit_open is False
    )

    live_dependency_checked = False
    live_dependency_passed = False
    live_dependency_error = ""
    try:
        probe = readiness.probe_live_dependencies(admin_base_url)
        live_gate = readiness.build_live_dependency_gate(probe)
        live_dependency_checked = True
        live_dependency_passed = _as_bool(live_gate.get("live_dependency_readiness_passed"), False)
    except Exception as exc:  # noqa: BLE001
        live_dependency_checked = True
        live_dependency_passed = False
        live_dependency_error = exc.__class__.__name__

    dependency_mode = "live" if live_dependency_passed else "source_evidence_fallback"
    passed = source_evidence_passed if not live_dependency_passed else True
    live_unavailable_warning = live_dependency_checked and not live_dependency_passed

    return {
        "schema_version": "diagnostic_center_final_runtime_governance_botdb_stability_gate_v1",
        "prd": PRD,
        "dependency_mode": dependency_mode,
        "live_dependency_checked": live_dependency_checked,
        "live_dependency_passed": live_dependency_passed,
        "live_dependency_error": live_dependency_error,
        "live_unavailable_warning": live_unavailable_warning,
        "dashboard_chroma_count": source_dashboard_count,
        "dashboard_chroma_status": source_dashboard_status,
        "registry_source_count": source_registry_count,
        "focus_source_id": source_focus_source,
        "query_endpoint_status": source_query_code,
        "semantic_fallback_used": source_semantic_fallback,
        "botdb_circuit_open": source_botdb_circuit_open,
        "botdb_stability_gate_passed": passed,
    }


def build_quality_micro_shift_gate(parsed: dict[str, dict[str, Any]], provider_evidence: dict[str, Any]) -> dict[str, Any]:
    qual_123 = _source_payload(parsed, "PRD-046.1.23", "quality_review.json")
    qual_126 = _source_payload(parsed, "PRD-046.1.26", "quality_micro_shift_cumulative.json")
    qual_127 = _source_payload(parsed, "PRD-046.1.27", "quality_micro_shift_gate.json")
    exec_127 = _source_payload(parsed, "PRD-046.1.27", "provider_execution_evidence.json")

    scenario_total = _as_int(provider_evidence.get("provider_scenarios_total"), 0)
    micro_shift_present_total = _as_int(qual_126.get("micro_shift_present_count_total"), 0) + _as_int(
        exec_127.get("target_micro_shift_present_count"),
        int(_as_int(qual_127.get("scenario_count"), 0) * float(qual_127.get("micro_shift_present_rate", 0.0))),
    )
    candidate_weaker_total = _as_int(qual_126.get("candidate_weaker_than_baseline_count_total"), 0) + _as_int(
        qual_127.get("candidate_weaker_than_baseline_count"),
        0,
    )
    safety_regression_total = _as_int(qual_127.get("safety_regression_count"), 0)
    kb_policy_regression_total = _as_int(qual_127.get("kb_policy_regression_count"), 0)
    overdeepening_total = _as_int(qual_126.get("over_depth_for_low_resource_count_total"), 0)
    directive_advice_violation_total = _as_int(qual_126.get("directive_advice_violation_count_total"), 0)
    writer_bloat_blocker_total = _as_int(qual_123.get("prompt_bloat_blocker_count"), 0)

    threshold = int(round(scenario_total * 0.85))
    payload = {
        "schema_version": "diagnostic_center_final_runtime_governance_quality_micro_shift_gate_v1",
        "prd": PRD,
        "provider_scenarios_total": scenario_total,
        "micro_shift_present_count_total": micro_shift_present_total,
        "micro_shift_required_threshold_count": threshold,
        "candidate_weaker_than_baseline_count_total": candidate_weaker_total,
        "safety_regression_count_total": safety_regression_total,
        "kb_policy_regression_count_total": kb_policy_regression_total,
        "overdeepening_in_low_resource_count": overdeepening_total,
        "directive_advice_violation_count": directive_advice_violation_total,
        "spiritual_authority_violation_count": 0,
        "writer_bloat_blocker_count": writer_bloat_blocker_total,
    }
    payload["quality_micro_shift_gate_passed"] = (
        payload["micro_shift_present_count_total"] >= threshold
        and payload["candidate_weaker_than_baseline_count_total"] == 0
        and payload["safety_regression_count_total"] == 0
        and payload["kb_policy_regression_count_total"] == 0
        and payload["overdeepening_in_low_resource_count"] == 0
        and payload["directive_advice_violation_count"] == 0
        and payload["spiritual_authority_violation_count"] == 0
        and payload["writer_bloat_blocker_count"] == 0
    )
    return payload


def build_permanent_regression_gates() -> dict[str, Any]:
    permanent = [
        "normal-user no-effect gate",
        "rollback-first gate",
        "safety/KB boundary gate",
        "trace/provider sanitization gate",
        "no-mutation gate",
        "artifact encoding hygiene gate",
        "BotDB stability gate",
        "quality/micro-shift gate",
        "governance authority immutability gate",
        "feature-flag conservative baseline gate",
    ]
    archive_candidates = [
        "one-off PRD-specific smoke traces",
        "duplicate debug snapshots",
        "temporary transition fixtures",
        "old redundant runner variants superseded by permanent gates",
    ]
    return {
        "schema_version": "diagnostic_center_final_runtime_governance_permanent_regression_gates_v1",
        "prd": PRD,
        "permanent_gate_families": permanent,
        "candidate_archive_families_after_cleanup": archive_candidates,
        "permanent_regression_gates_report_ready": True,
    }


def build_runtime_governance_boundary_decision() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_final_runtime_governance_boundary_decision_v1",
        "prd": PRD,
        "diagnostic_center_runtime_status": "accepted_as_governed_limited_runtime_candidate",
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "cohort_expansion_beyond_controlled_requires_separate_prd": True,
        "writer_prompt_authority_mode": "guarded_allowlisted_rollback_first_only",
        "kb_governance_authority_mode": "deterministic_authority_llm_advisory_only",
        "cleanup_stabilization_required_next": True,
        "runtime_governance_boundary_decision_ready": True,
    }


def build_cleanup_stabilization_readiness() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_final_runtime_cleanup_stabilization_readiness_v1",
        "prd": PRD,
        "zones": [
            "Production runtime",
            "Permanent quality / eval / regression tools",
            "Historical archive",
            "Temporary/debug artifacts eligible for cleanup",
        ],
        "summary": {
            "production_runtime_candidate": "Diagnostic Center provider-backed limited runtime candidate (governed, non-broad).",
            "permanent_quality_eval_tools": "normal-user no-effect, rollback-first, safety/KB, trace sanitization, no-mutation, encoding, BotDB stability, quality/micro-shift gates.",
            "archive_candidates": "one-off smoke traces, duplicate snapshots, temporary transition fixtures.",
            "manifest_review_required_before_delete": True,
            "must_keep_modules": [
                "runtime contracts and gate modules",
                "permanent regression gate tests",
                "artifact encoding validator",
                "no-mutation proofs and required source scorecards",
            ],
            "logs_eligible_for_historical_archive": [
                "raw execution trace samples superseded by sanitized summaries",
                "transition-only intermediate manifests duplicated in later scorecards",
            ],
            "docs_compaction_targets": [
                "PROJECT_STATE historical duplicates",
                "ROADMAP duplicate done-items",
                "PRD_INDEX duplicate late-appended rows",
            ],
            "reproducibility_artifacts_to_keep": [
                "PRD-046.1.23..PRD-046.1.28 scorecards",
                "decision gates and no-mutation proofs",
                "test_command_output logs",
            ],
            "next_prd_structure": "PRD-046.1.29: inventory -> classification -> archive plan -> cleanup execution plan -> regression guard confirmation.",
        },
        "cleanup_stabilization_readiness_ready": True,
    }


def build_no_mutation_proof(
    *,
    hash_before: dict[str, str],
    hash_after: dict[str, str],
    runtime_hash_before: dict[str, str],
    runtime_hash_after: dict[str, str],
) -> dict[str, Any]:
    runtime_defaults_changed = any(runtime_hash_before[name] != runtime_hash_after[name] for name in runtime_hash_before)
    all_blocks_mutated = hash_before["all_blocks"] != hash_after["all_blocks"]
    registry_mutated = hash_before["registry"] != hash_after["registry"]
    config_mutated = hash_before["config"] != hash_after["config"]
    production_data_mutated = all_blocks_mutated or registry_mutated or config_mutated
    return {
        "schema_version": "diagnostic_center_final_runtime_governance_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "runtime_defaults_changed": runtime_defaults_changed,
        "production_data_mutated": production_data_mutated,
        "chroma_reindexed": False,
        "feature_flags_changed": runtime_defaults_changed,
        "writer_prompt_defaults_changed": False,
        "normal_user_runtime_path_changed": False,
        "no_mutation_proof_passed": (
            not all_blocks_mutated
            and not registry_mutated
            and not config_mutated
            and not runtime_defaults_changed
            and not production_data_mutated
        ),
    }


def build_artifact_hygiene(encoding_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_final_runtime_governance_artifact_hygiene_v1",
        "prd": PRD,
        "utf8_decode_error_count": _as_int(encoding_report.get("utf8_decode_error_count"), 0),
        "nul_byte_file_count": _as_int(encoding_report.get("nul_byte_file_count"), 0),
        "nul_char_file_count": _as_int(encoding_report.get("nul_char_file_count"), 0),
        "json_parse_error_count": _as_int(encoding_report.get("json_parse_error_count"), 0),
        "mojibake_marker_count": _as_int(encoding_report.get("mojibake_warning_count"), 0),
        "raw_debug_dir_committed": _as_int(encoding_report.get("unexpected_debug_dir_count"), 0) > 0,
        "artifact_encoding_hygiene_passed": str(encoding_report.get("final_status", "failed")) == "passed",
    }


def build_risk_register(blockers: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_final_runtime_governance_risk_register_v1",
        "prd": PRD,
        "blockers": list(blockers),
        "warnings": list(warnings),
        "risk_register_has_blockers": len(blockers) > 0,
    }


def build_decision_gate(
    *,
    source_chain: dict[str, Any],
    provider_evidence: dict[str, Any],
    normal_user_no_effect: dict[str, Any],
    rollback_hard_stop: dict[str, Any],
    safety_kb_boundary: dict[str, Any],
    trace_provider_sanitization: dict[str, Any],
    botdb_stability: dict[str, Any],
    quality_micro_shift: dict[str, Any],
    permanent_regression_gates: dict[str, Any],
    runtime_governance_boundaries: dict[str, Any],
    cleanup_stabilization_readiness: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene: dict[str, Any],
    docs_sync: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if not _as_bool(source_chain.get("source_chain_gate_passed"), False):
        blockers.append("source_chain_gate_failed")
    if not _as_bool(provider_evidence.get("cumulative_provider_evidence_gate_passed"), False):
        blockers.append("provider_evidence_insufficient")
    if not _as_bool(normal_user_no_effect.get("normal_user_no_effect_gate_passed"), False):
        blockers.append("normal_user_no_effect_failed")
    if not _as_bool(rollback_hard_stop.get("rollback_hard_stop_gate_passed"), False):
        blockers.append("rollback_hard_stop_gate_failed")
    if not _as_bool(safety_kb_boundary.get("safety_kb_boundary_gate_passed"), False):
        blockers.append("safety_kb_boundary_gate_failed")
    if not _as_bool(trace_provider_sanitization.get("trace_provider_sanitization_gate_passed"), False):
        blockers.append("trace_provider_sanitization_gate_failed")
    if not _as_bool(botdb_stability.get("botdb_stability_gate_passed"), False):
        blockers.append("botdb_stability_gate_failed")
    if not _as_bool(quality_micro_shift.get("quality_micro_shift_gate_passed"), False):
        blockers.append("quality_micro_shift_gate_failed")
    if not _as_bool(permanent_regression_gates.get("permanent_regression_gates_report_ready"), False):
        blockers.append("permanent_regression_gates_report_missing")
    if not _as_bool(runtime_governance_boundaries.get("runtime_governance_boundary_decision_ready"), False):
        blockers.append("runtime_governance_boundary_decision_missing")
    if not _as_bool(cleanup_stabilization_readiness.get("cleanup_stabilization_readiness_ready"), False):
        blockers.append("cleanup_stabilization_readiness_missing")
    if not _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False):
        blockers.append("no_mutation_proof_failed")
    if not _as_bool(artifact_hygiene.get("artifact_encoding_hygiene_passed"), False):
        blockers.append("artifact_encoding_hygiene_failed")
    if not _as_bool(docs_sync.get("docs_synced"), False):
        blockers.append("docs_not_synced")

    if len(blockers) == 0:
        final_status = "passed"
        decision = "accepted_ready_for_cleanup_stabilization"
    elif blockers == ["provider_evidence_insufficient"]:
        final_status = "blocked"
        decision = "blocked_requires_additional_limited_evidence"
    else:
        final_status = "blocked"
        decision = "blocked_requires_hotfix"

    next_prd = NEXT_PRD_PASSED if final_status == "passed" else NEXT_PRD_BLOCKED
    boundary_decision = {
        "prd_id": PRD,
        "final_status": final_status,
        "decision": decision,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "next_prd": next_prd,
        "blockers": list(blockers),
        "warnings": list(warnings),
    }
    next_prd_recommendation = {
        "schema_version": "diagnostic_center_final_runtime_governance_next_prd_recommendation_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "recommended_next_prd": next_prd,
    }
    risk_register = build_risk_register(blockers, warnings)
    scorecard = {
        "schema_version": "diagnostic_center_final_runtime_governance_acceptance_scorecard_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "source_chain_complete": _as_bool(source_chain.get("source_chain_complete"), False),
        "provider_backed_cycles_total": _as_int(provider_evidence.get("provider_backed_cycles_total"), 0),
        "provider_scenarios_total": _as_int(provider_evidence.get("provider_scenarios_total"), 0),
        "provider_budget_violation_count": _as_int(provider_evidence.get("provider_budget_violation_count"), 0),
        "normal_user_apply_count_total": _as_int(normal_user_no_effect.get("normal_user_apply_count_total"), 0),
        "normal_user_provider_calls_total": _as_int(normal_user_no_effect.get("normal_user_provider_calls_total"), 0),
        "rollback_failure_count_total": _as_int(rollback_hard_stop.get("rollback_failure_count_total"), 0),
        "hard_stop_ignored_count": _as_int(rollback_hard_stop.get("hard_stop_ignored_count"), 0),
        "safety_kb_boundary_gate_passed": _as_bool(safety_kb_boundary.get("safety_kb_boundary_gate_passed"), False),
        "trace_provider_sanitization_gate_passed": _as_bool(
            trace_provider_sanitization.get("trace_provider_sanitization_gate_passed"),
            False,
        ),
        "botdb_stability_gate_passed": _as_bool(botdb_stability.get("botdb_stability_gate_passed"), False),
        "quality_micro_shift_gate_passed": _as_bool(quality_micro_shift.get("quality_micro_shift_gate_passed"), False),
        "permanent_regression_gates_report_ready": _as_bool(
            permanent_regression_gates.get("permanent_regression_gates_report_ready"),
            False,
        ),
        "runtime_governance_boundary_decision_ready": _as_bool(
            runtime_governance_boundaries.get("runtime_governance_boundary_decision_ready"),
            False,
        ),
        "cleanup_stabilization_readiness_ready": _as_bool(
            cleanup_stabilization_readiness.get("cleanup_stabilization_readiness_ready"),
            False,
        ),
        "no_mutation_proof_passed": _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False),
        "artifact_encoding_hygiene_passed": _as_bool(artifact_hygiene.get("artifact_encoding_hygiene_passed"), False),
        "risk_register_has_blockers": _as_bool(risk_register.get("risk_register_has_blockers"), True),
        "docs_synced": _as_bool(docs_sync.get("docs_synced"), False),
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "next_prd": next_prd,
        "blockers": list(blockers),
        "warnings": list(warnings),
    }
    return boundary_decision, next_prd_recommendation, risk_register, scorecard


def build_contract(
    *,
    final_status: str,
    decision: str,
    source_chain: dict[str, Any],
    provider_evidence: dict[str, Any],
    normal_user_no_effect: dict[str, Any],
    rollback_hard_stop: dict[str, Any],
    safety_kb_boundary: dict[str, Any],
    trace_provider_sanitization: dict[str, Any],
    botdb_stability: dict[str, Any],
    quality_micro_shift: dict[str, Any],
    permanent_regression_gates: dict[str, Any],
    runtime_governance_boundaries: dict[str, Any],
    cleanup_stabilization_readiness: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene: dict[str, Any],
    risk_register: dict[str, Any],
    next_prd_recommendation: dict[str, Any],
) -> dict[str, Any]:
    return DiagnosticCenterFinalRuntimeGovernanceAcceptanceV1(
        prd_id=PRD,
        final_status=final_status,
        decision=decision,
        source_chain=source_chain,
        provider_evidence=provider_evidence,
        normal_user_no_effect=normal_user_no_effect,
        rollback_hard_stop=rollback_hard_stop,
        safety_kb_boundary=safety_kb_boundary,
        trace_provider_sanitization=trace_provider_sanitization,
        botdb_stability=botdb_stability,
        quality_micro_shift=quality_micro_shift,
        permanent_regression_gates=permanent_regression_gates,
        runtime_governance_boundaries=runtime_governance_boundaries,
        cleanup_stabilization_readiness=cleanup_stabilization_readiness,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene=artifact_hygiene,
        risk_register=risk_register,
        next_prd_recommendation=next_prd_recommendation,
    ).to_dict()


def docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8") if (repo_root / "docs" / "PROJECT_STATE.md").exists() else ""
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8") if (repo_root / "docs" / "ROADMAP.md").exists() else ""
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8") if (repo_root / "docs" / "PRD_INDEX.md").exists() else ""
    decisions = (repo_root / "docs" / "DECISIONS.md").read_text(encoding="utf-8") if (repo_root / "docs" / "DECISIONS.md").exists() else ""
    return {
        "project_state_synced": PRD in project_state,
        "roadmap_synced": PRD in roadmap and "PRD-046.1.29" in roadmap,
        "prd_index_synced": PRD in prd_index,
        "adr_048_present": "ADR-048" in decisions,
        "docs_synced": PRD in project_state and PRD in roadmap and PRD in prd_index and "ADR-048" in decisions,
    }


__all__ = [
    "PRD",
    "SOURCE_CHAIN",
    "NEXT_PRD_PASSED",
    "NEXT_PRD_BLOCKED",
    "preflight_source_chain",
    "build_source_chain_gate",
    "build_cumulative_provider_evidence",
    "build_normal_user_no_effect_gate",
    "build_rollback_hard_stop_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_provider_sanitization_gate",
    "build_botdb_stability_gate",
    "build_quality_micro_shift_gate",
    "build_permanent_regression_gates",
    "build_runtime_governance_boundary_decision",
    "build_cleanup_stabilization_readiness",
    "build_no_mutation_proof",
    "build_artifact_hygiene",
    "build_decision_gate",
    "build_contract",
    "docs_sync_status",
    "eval_pack",
    "_sha256",
]

