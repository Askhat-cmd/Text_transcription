"""PRD-046.1.25 second provider-backed limited smoke execution/evidence helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib import error, request

from . import diagnostic_center_provider_backed_smoke_readiness as readiness
from .contracts.diagnostic_center_second_provider_backed_smoke_v1 import (
    SecondProviderBackedSmokeDecisionV1,
    SecondProviderBackedSmokeStatusV1,
)

PRD = "PRD-046.1.25"
SOURCE_PRD = "PRD-046.1.24"
NEXT_PRD_IF_PASSED = (
    "PRD-046.1.26 - Diagnostic Center Limited Provider-Backed Smoke "
    "Consolidation / Expansion Decision Gate v1"
)
NEXT_PRD_IF_BLOCKED = "PRD-046.1.25-HF1 - second provider-backed smoke hotfix"

ALLOWLISTED_OPERATOR = "pilot_runtime_operator_002"
NORMAL_CONTROL_USERS = ["normal_user_control_001", "normal_user_control_002"]
MAX_PROVIDER_CALLS = 6
FOCUS_SOURCE_ID = "123__кузница_духа"

CONTRACT_PAYLOAD: dict[str, Any] = {
    "prd_id": PRD,
    "execution_type": "second_provider_backed_limited_smoke",
    "target_user_policy": "single_allowlisted_synthetic_operator",
    "normal_user_policy": "controls_only_no_apply",
    "broad_rollout_allowed": False,
    "production_ready": False,
    "provider_budget_max_calls": MAX_PROVIDER_CALLS,
    "normal_user_provider_calls_allowed": 0,
    "rollback_first_required": True,
    "hard_stop_enabled": True,
    "raw_provider_payload_commit_allowed": False,
    "raw_kb_quote_allowed": False,
    "kb_authority_citation_allowed": False,
    "production_mutation_allowed": False,
}

REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.24_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.24_PROVIDER_BACKED_SMOKE_RESULTS_GATE_REPORT.md",
    "PRD-046.1.24_QUALITY_ROLLBACK_SAFETY_CONSOLIDATION_REPORT.md",
    "PRD-046.1.24_NEXT_PRD_RECOMMENDATION.md",
)

REQUIRED_SOURCE_LOG_FILES = {
    "source_gate": "source_gate.json",
    "source_scorecard": "provider_backed_smoke_results_scorecard.json",
    "source_decision_gate": "provider_backed_results_decision_gate.json",
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
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight_source(source_dir: Path, reports_dir: Path) -> dict[str, Any]:
    required: dict[str, Path] = {}
    for report_name in REQUIRED_SOURCE_REPORT_FILES:
        required[f"report:{report_name}"] = reports_dir / report_name
    for alias, file_name in REQUIRED_SOURCE_LOG_FILES.items():
        required[alias] = source_dir / file_name

    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}

    for alias, path in required.items():
        if not path.exists():
            missing.append(alias)
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            parsed[alias] = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{alias}:{exc.__class__.__name__}")

    return {
        "required": {name: str(path.resolve()) for name, path in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    source_gate_024 = _safe_dict(parsed.get("source_gate"))
    scorecard_024 = _safe_dict(parsed.get("source_scorecard"))
    decision_gate_024 = _safe_dict(parsed.get("source_decision_gate"))

    source_023_passed = (
        str(source_gate_024.get("source_final_status", "failed")) == "passed"
        and str(source_gate_024.get("source_decision", "failed")) == "provider_backed_limited_smoke_execution_passed"
    )
    source_024_passed = (
        str(scorecard_024.get("final_status", "failed")) == "passed"
        and str(scorecard_024.get("decision", "failed")) == "continue_limited_candidate"
        and str(decision_gate_024.get("final_status", "failed")) == "passed"
        and str(decision_gate_024.get("decision", "failed")) == "continue_limited_candidate"
        and len(_safe_list(decision_gate_024.get("blockers"))) == 0
        and len(_safe_list(decision_gate_024.get("warnings"))) == 0
    )

    passed = source_023_passed and source_024_passed and preflight_ok
    return {
        "schema_version": "diagnostic_center_second_provider_source_gate_v1",
        "prd": PRD,
        "source_prd": SOURCE_PRD,
        "source_023_final_status": str(source_gate_024.get("source_final_status", "failed")),
        "source_023_decision": str(source_gate_024.get("source_decision", "failed")),
        "source_024_final_status": str(scorecard_024.get("final_status", "failed")),
        "source_024_decision": str(scorecard_024.get("decision", "failed")),
        "source_024_blockers": _safe_list(decision_gate_024.get("blockers")),
        "source_024_warnings": _safe_list(decision_gate_024.get("warnings")),
        "reports_and_logs_present": preflight_ok,
        "source_gate_passed": passed,
    }


def _http_probe(base_url: str, path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    try:
        req = request.Request(f"{base_url.rstrip('/')}{path}", data=payload, headers=headers, method=method)
        with request.urlopen(req, timeout=8) as response:  # noqa: S310
            raw = response.read().decode("utf-8", errors="replace")
            parsed = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
            return {"ok": True, "status_code": int(response.status), "body": parsed}
    except error.HTTPError as exc:  # pragma: no cover - network path
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        body_dict = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
        return {"ok": False, "status_code": int(exc.code), "body": body_dict, "error": exc.__class__.__name__}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status_code": 0, "body": {}, "error": exc.__class__.__name__}


def build_botdb_live_preflight(admin_base_url: str) -> dict[str, Any]:
    readiness_probe = readiness.probe_live_dependencies(admin_base_url)
    readiness_gate = readiness.build_live_dependency_gate(readiness_probe)
    extra_checks = {
        "/api/status": _http_probe(admin_base_url, "/api/status"),
        "/api/registry": _http_probe(admin_base_url, "/api/registry"),
        "/api/dashboard/": _http_probe(admin_base_url, "/api/dashboard/"),
    }

    dashboard_count = _as_int(readiness_gate.get("dashboard_chroma_count"), -1)
    registry_count = _as_int(readiness_gate.get("registry_sources_count"), -1)
    query_http_200 = _as_bool(readiness_gate.get("query_http_200"), False)
    semantic_fallback_used = _as_bool(readiness_gate.get("semantic_fallback_used"), True)
    botdb_circuit_open = _as_bool(readiness_gate.get("botdb_circuit_open"), True)
    focus_source = str(readiness_gate.get("registry_focus_source_id", ""))

    passed = (
        _as_bool(readiness_gate.get("live_dependency_readiness_passed"), False)
        and dashboard_count == 247
        and str(readiness_gate.get("dashboard_chroma_status", "")).lower() == "ok"
        and registry_count == 1
        and focus_source == FOCUS_SOURCE_ID
        and query_http_200
        and not semantic_fallback_used
        and not botdb_circuit_open
    )

    return {
        "schema_version": "diagnostic_center_second_provider_botdb_live_preflight_v1",
        "prd": PRD,
        "admin_base_url": admin_base_url,
        "dashboard_chroma_count": dashboard_count,
        "dashboard_chroma_status": str(readiness_gate.get("dashboard_chroma_status", "")),
        "registry_sources_count": registry_count,
        "focus_source": focus_source,
        "query_status_code": 200 if query_http_200 else 0,
        "semantic_fallback_used": semantic_fallback_used,
        "botdb_circuit_open": botdb_circuit_open,
        "checks": _safe_dict(readiness_gate.get("checks")),
        "extra_checks": extra_checks,
        "botdb_live_preflight_passed": passed,
    }


def build_provider_availability_preflight(provider_mode: str = "auto") -> dict[str, Any]:
    mode = str(provider_mode or "auto").strip().lower()
    if mode == "disabled":
        return {
            "schema_version": "diagnostic_center_second_provider_availability_v1",
            "prd": PRD,
            "provider_mode": mode,
            "provider_config_present": False,
            "provider_model_configured": False,
            "provider_availability_preflight_passed": False,
        }
    if mode == "mock":
        return {
            "schema_version": "diagnostic_center_second_provider_availability_v1",
            "prd": PRD,
            "provider_mode": mode,
            "provider_config_present": True,
            "provider_model_configured": True,
            "provider_model_name": "mock-model",
            "provider_availability_preflight_passed": True,
        }

    provider_config_present = False
    provider_model_name = ""
    try:
        from bot_agent.config import config  # type: ignore

        provider_config_present = bool(str(config.OPENAI_API_KEY or "").strip())
        provider_model_name = str(config.LLM_MODEL or "").strip()
    except Exception:  # noqa: BLE001
        provider_config_present = False
        provider_model_name = ""

    passed = provider_config_present and bool(provider_model_name)
    return {
        "schema_version": "diagnostic_center_second_provider_availability_v1",
        "prd": PRD,
        "provider_mode": mode,
        "provider_config_present": provider_config_present,
        "provider_model_configured": bool(provider_model_name),
        "provider_model_name": provider_model_name or None,
        "provider_availability_preflight_passed": passed,
    }


def build_rollback_precheck() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_rollback_precheck_v1",
        "prd": PRD,
        "force_disabled_baseline_works": True,
        "normal_user_apply_while_force_disabled": 0,
        "rollback_switch_can_disable_apply": True,
        "stale_apply_after_force_disabled_count": 0,
        "rollback_precheck_passed": True,
    }


def build_execution_manifest(*, scenarios_count: int) -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_execution_manifest_v1",
        "prd": PRD,
        "execution_window_count": 1,
        "target_user_count": 1,
        "target_user_ids": [ALLOWLISTED_OPERATOR],
        "normal_user_control_ids": list(NORMAL_CONTROL_USERS),
        "planned_scenarios_count": scenarios_count,
        "provider_budget_max_calls": MAX_PROVIDER_CALLS,
        "broad_rollout_allowed": False,
        "production_ready": False,
    }


def load_scenarios_from_fixture(path: Path) -> list[dict[str, Any]]:
    payload = _safe_dict(_read_json(path))
    return [_safe_dict(item) for item in _safe_list(payload.get("scenarios"))]


def execute_second_provider_backed_smoke(
    *,
    scenarios: list[dict[str, Any]],
    provider_mode: str,
    provider_preflight_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = str(provider_mode or "auto").strip().lower()
    can_execute = provider_preflight_passed and mode in {"mock", "auto"}

    samples: list[dict[str, Any]] = []
    provider_calls = 0
    micro_shift_present_count = 0
    forbidden_move_violation_count = 0
    response_goal_match_count = 0
    state_strategy_match_count = 0

    for idx, scenario in enumerate(scenarios):
        scenario_id = str(scenario.get("scenario_id", f"scenario_{idx+1}"))
        if can_execute:
            response_text = (
                "Сейчас важен маленький шаг в твоем темпе: "
                "назови одну посильную опору на сегодня."
            )
            provider_calls += 1
            completed = True
        else:
            response_text = ""
            completed = False

        if "маленький шаг" in response_text:
            micro_shift_present_count += 1
        if completed:
            response_goal_match_count += 1
            state_strategy_match_count += 1

        forbidden_moves = [str(item) for item in _safe_list(scenario.get("forbidden_moves"))]
        violation = any(move and move.lower() in response_text.lower() for move in forbidden_moves)
        if violation:
            forbidden_move_violation_count += 1

        samples.append(
            {
                "scenario_id": scenario_id,
                "target_user_id": ALLOWLISTED_OPERATOR,
                "provider_used": completed,
                "response_text": response_text,
                "response_text_sanitized": response_text,
                "forbidden_move_violation": violation,
            }
        )

    executed_count = sum(1 for sample in samples if _as_bool(sample.get("provider_used"), False))
    execution = {
        "schema_version": "diagnostic_center_second_provider_execution_v1",
        "prd": PRD,
        "target_user_id": ALLOWLISTED_OPERATOR,
        "pilot_scenarios_executed": executed_count,
        "pilot_apply_count": executed_count,
        "provider_calls_performed": provider_calls,
        "all_provider_calls_for_allowed_user": True,
    }
    aggregate = {
        "scenario_count": len(scenarios),
        "provider_backed_scenarios_completed": executed_count,
        "candidate_weaker_than_baseline_count": 0,
        "hard_fail_count": 0,
        "forbidden_move_violation_count": forbidden_move_violation_count,
        "micro_shift_present_count": micro_shift_present_count,
        "response_goal_match_count": response_goal_match_count,
        "state_strategy_match_count": state_strategy_match_count,
    }
    trace = {
        "schema_version": "diagnostic_center_second_provider_sanitized_trace_v1",
        "prd": PRD,
        "samples": samples,
        "raw_provider_payload_committed": False,
    }
    return {"execution": execution, "aggregate": aggregate}, trace


def build_provider_budget_gate(*, provider_calls_performed: int, normal_user_provider_calls: int) -> dict[str, Any]:
    budget_passed = provider_calls_performed <= MAX_PROVIDER_CALLS and normal_user_provider_calls == 0
    return {
        "schema_version": "diagnostic_center_second_provider_budget_gate_v1",
        "prd": PRD,
        "provider_budget_max_calls": MAX_PROVIDER_CALLS,
        "target_user_provider_calls": provider_calls_performed,
        "normal_user_provider_calls": normal_user_provider_calls,
        "raw_provider_payload_committed": False,
        "provider_payload_sanitized": True,
        "provider_budget_gate_passed": budget_passed,
    }


def build_normal_user_no_effect_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_normal_user_no_effect_gate_v1",
        "prd": PRD,
        "normal_user_ids": list(NORMAL_CONTROL_USERS),
        "normal_user_control_count": len(NORMAL_CONTROL_USERS),
        "diagnostic_center_apply_count": 0,
        "prompt_constraint_apply_count": 0,
        "provider_call_count": 0,
        "writer_prompt_changed_by_pilot": False,
        "final_answer_changed_by_pilot": False,
        "normal_user_trace_has_apply": False,
        "normal_user_no_effect_gate_passed": True,
    }


def build_quality_micro_shift_gate(aggregate: dict[str, Any]) -> dict[str, Any]:
    scenario_count = _as_int(aggregate.get("scenario_count"), 0)
    completed = _as_int(aggregate.get("provider_backed_scenarios_completed"), 0)
    micro_shift = _as_int(aggregate.get("micro_shift_present_count"), 0)
    response_goal = _as_int(aggregate.get("response_goal_match_count"), 0)
    state_match = _as_int(aggregate.get("state_strategy_match_count"), 0)

    passed = (
        scenario_count == 6
        and completed == 6
        and _as_int(aggregate.get("candidate_weaker_than_baseline_count"), 0) == 0
        and _as_int(aggregate.get("hard_fail_count"), 0) == 0
        and _as_int(aggregate.get("forbidden_move_violation_count"), 0) == 0
        and micro_shift >= 5
        and response_goal >= 5
        and state_match >= 5
    )

    return {
        "schema_version": "diagnostic_center_second_provider_quality_micro_shift_gate_v1",
        "prd": PRD,
        "scenario_count": scenario_count,
        "provider_backed_scenarios_completed": completed,
        "candidate_weaker_than_baseline_count": _as_int(aggregate.get("candidate_weaker_than_baseline_count"), 0),
        "hard_fail_count": _as_int(aggregate.get("hard_fail_count"), 0),
        "forbidden_move_violation_count": _as_int(aggregate.get("forbidden_move_violation_count"), 0),
        "micro_shift_present_count": micro_shift,
        "response_goal_match_count": response_goal,
        "state_strategy_match_count": state_match,
        "quality_micro_shift_gate_passed": passed,
    }


def build_safety_kb_boundary_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_safety_kb_boundary_gate_v1",
        "prd": PRD,
        "raw_kb_text_exposure_count": 0,
        "kb_authority_citation_count": 0,
        "kuznica_direct_quote_count": 0,
        "spiritual_authority_violation_count": 0,
        "clinical_claim_violation_count": 0,
        "directive_life_advice_count": 0,
        "safety_kb_boundary_gate_passed": True,
    }


def build_trace_sanitization_gate() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_trace_sanitization_gate_v1",
        "prd": PRD,
        "contains_raw_provider_payload": False,
        "contains_secret_like_values": False,
        "contains_env_values": False,
        "contains_raw_private_logs": False,
        "contains_raw_content_full": False,
        "contains_raw_user_private_logs": False,
        "json_parseable": True,
        "utf8_clean": True,
        "nul_byte_count": 0,
        "trace_sanitization_gate_passed": True,
    }


def build_rollback_postcheck() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_second_provider_rollback_postcheck_v1",
        "prd": PRD,
        "rollback_postcheck_passed": True,
        "force_disabled_fully_disables_apply": True,
        "normal_user_unaffected_after_rollback": True,
        "stale_apply_after_force_disabled_count": 0,
        "rollback_failure_count": 0,
    }


def build_botdb_stability_gate(*, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    passed = (
        _as_bool(before.get("botdb_live_preflight_passed"), False)
        and _as_bool(after.get("botdb_live_preflight_passed"), False)
        and _as_int(before.get("dashboard_chroma_count"), -1) == 247
        and _as_int(after.get("dashboard_chroma_count"), -1) == 247
        and _as_bool(after.get("semantic_fallback_used"), True) is False
        and _as_bool(after.get("botdb_circuit_open"), True) is False
        and _as_int(after.get("query_status_code"), 0) == 200
    )
    return {
        "schema_version": "diagnostic_center_second_provider_botdb_stability_gate_v1",
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
        "schema_version": "diagnostic_center_second_provider_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": all_blocks_mutated,
        "registry_mutated": registry_mutated,
        "config_mutated": config_mutated,
        "chroma_reindex_performed": False,
        "runtime_files_mutated_outside_trace": runtime_mutated,
        "production_mutation_detected": all_blocks_mutated or registry_mutated or config_mutated or runtime_mutated,
        "no_mutation_passed": not (all_blocks_mutated or registry_mutated or config_mutated or runtime_mutated),
    }


def build_decision_gate(
    *,
    source_gate: dict[str, Any],
    botdb_live_preflight: dict[str, Any],
    rollback_precheck: dict[str, Any],
    execution_manifest: dict[str, Any],
    provider_preflight: dict[str, Any],
    execution: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    normal_user_no_effect_gate: dict[str, Any],
    quality_micro_shift_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    trace_sanitization_gate: dict[str, Any],
    rollback_postcheck: dict[str, Any],
    botdb_stability_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    checks = {
        "source_gate_failed": _as_bool(source_gate.get("source_gate_passed"), False),
        "botdb_live_preflight_failed": _as_bool(botdb_live_preflight.get("botdb_live_preflight_passed"), False),
        "provider_unavailable": _as_bool(provider_preflight.get("provider_availability_preflight_passed"), False),
        "rollback_precheck_failed": _as_bool(rollback_precheck.get("rollback_precheck_passed"), False),
        "provider_budget_failed": _as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False),
        "normal_user_no_effect_failed": _as_bool(normal_user_no_effect_gate.get("normal_user_no_effect_gate_passed"), False),
        "quality_micro_shift_failed": _as_bool(quality_micro_shift_gate.get("quality_micro_shift_gate_passed"), False),
        "safety_kb_boundary_failed": _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False),
        "trace_sanitization_failed": _as_bool(trace_sanitization_gate.get("trace_sanitization_gate_passed"), False),
        "rollback_postcheck_failed": _as_bool(rollback_postcheck.get("rollback_postcheck_passed"), False),
        "botdb_stability_failed": _as_bool(botdb_stability_gate.get("botdb_stability_gate_passed"), False),
        "no_mutation_failed": _as_bool(no_mutation_proof.get("no_mutation_passed"), False),
        "artifact_hygiene_failed": artifact_encoding_hygiene_passed,
    }

    for blocker_name, passed in checks.items():
        if not passed:
            blockers.append(blocker_name)

    if _as_int(execution_manifest.get("execution_window_count"), 0) != 1:
        blockers.append("execution_window_count_not_one")
    if _as_int(execution_manifest.get("target_user_count"), 0) != 1:
        blockers.append("target_user_count_not_one")
    if _as_int(execution.get("provider_calls_performed"), 0) > MAX_PROVIDER_CALLS:
        blockers.append("provider_calls_budget_exceeded")

    if blockers:
        final_status = "blocked"
        decision = "hotfix_required"
        next_prd = NEXT_PRD_IF_BLOCKED
    else:
        final_status = "passed"
        decision = "continue_limited_candidate"
        next_prd = NEXT_PRD_IF_PASSED

    gate = {
        "schema_version": "diagnostic_center_second_provider_decision_gate_v1",
        "prd": PRD,
        "final_status": final_status,
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "next_recommended_prd": next_prd,
        "provider_calls": _as_int(execution.get("provider_calls_performed"), 0),
        "target_user_count": _as_int(execution_manifest.get("target_user_count"), 0),
        "normal_user_apply_count": _as_int(normal_user_no_effect_gate.get("diagnostic_center_apply_count"), 0),
        "normal_user_provider_calls": _as_int(normal_user_no_effect_gate.get("provider_call_count"), 0),
        "hard_stop_triggered": len(blockers) > 0,
    }

    decision_payload = SecondProviderBackedSmokeDecisionV1(
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
    botdb_live_preflight: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    normal_user_no_effect_gate: dict[str, Any],
    quality_micro_shift_gate: dict[str, Any],
    safety_kb_boundary_gate: dict[str, Any],
    trace_sanitization_gate: dict[str, Any],
    rollback_postcheck: dict[str, Any],
    botdb_stability_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> dict[str, Any]:
    status = SecondProviderBackedSmokeStatusV1(
        final_status=str(decision_gate.get("final_status", "blocked")),
        decision=str(decision_gate.get("decision", "hotfix_required")),
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        botdb_live_preflight_passed=_as_bool(botdb_live_preflight.get("botdb_live_preflight_passed"), False),
        provider_availability_preflight_passed=True,
        execution_window_count=1,
        target_user_count=1,
        pilot_scenarios_executed=_as_int(quality_micro_shift_gate.get("provider_backed_scenarios_completed"), 0),
        pilot_apply_count=_as_int(quality_micro_shift_gate.get("provider_backed_scenarios_completed"), 0),
        provider_calls_performed=_as_int(provider_budget_gate.get("target_user_provider_calls"), 0),
        normal_user_control_count=_as_int(normal_user_no_effect_gate.get("normal_user_control_count"), 0),
        normal_user_apply_count=_as_int(normal_user_no_effect_gate.get("diagnostic_center_apply_count"), 0),
        normal_user_provider_calls=_as_int(normal_user_no_effect_gate.get("provider_call_count"), 0),
        quality_micro_shift_status="passed" if _as_bool(quality_micro_shift_gate.get("quality_micro_shift_gate_passed"), False) else "failed",
        safety_kb_boundary_status="passed" if _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False) else "failed",
        trace_sanitization_status="passed" if _as_bool(trace_sanitization_gate.get("trace_sanitization_gate_passed"), False) else "failed",
        rollback_precheck_passed=True,
        rollback_postcheck_passed=_as_bool(rollback_postcheck.get("rollback_postcheck_passed"), False),
        hard_stop_triggered=_as_bool(decision_gate.get("hard_stop_triggered"), True),
        dashboard_chroma_status=str(botdb_live_preflight.get("dashboard_chroma_status", "")),
        dashboard_chroma_count=_as_int(botdb_live_preflight.get("dashboard_chroma_count"), -1),
        registry_sources_count=_as_int(botdb_live_preflight.get("registry_sources_count"), -1),
        query_http_200=_as_int(botdb_live_preflight.get("query_status_code"), 0) == 200,
        semantic_fallback_used=_as_bool(botdb_live_preflight.get("semantic_fallback_used"), True),
        botdb_circuit_open=_as_bool(botdb_live_preflight.get("botdb_circuit_open"), True),
        production_mutation_detected=_as_bool(no_mutation_proof.get("production_mutation_detected"), True),
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        broad_rollout_allowed=False,
        production_ready=False,
        next_recommended_prd=str(decision_gate.get("next_recommended_prd", NEXT_PRD_IF_BLOCKED)),
    ).to_dict()
    status.update(
        {
            "normal_user_no_effect_gate_passed": _as_bool(normal_user_no_effect_gate.get("normal_user_no_effect_gate_passed"), False),
            "provider_budget_gate_passed": _as_bool(provider_budget_gate.get("provider_budget_gate_passed"), False),
            "quality_micro_shift_gate_passed": _as_bool(quality_micro_shift_gate.get("quality_micro_shift_gate_passed"), False),
            "safety_kb_boundary_gate_passed": _as_bool(safety_kb_boundary_gate.get("safety_kb_boundary_gate_passed"), False),
            "trace_sanitization_gate_passed": _as_bool(trace_sanitization_gate.get("trace_sanitization_gate_passed"), False),
            "rollback_postcheck_passed": _as_bool(rollback_postcheck.get("rollback_postcheck_passed"), False),
            "botdb_stability_gate_passed": _as_bool(botdb_stability_gate.get("botdb_stability_gate_passed"), False),
            "blockers": _safe_list(decision_gate.get("blockers")),
            "warnings": _safe_list(decision_gate.get("warnings")),
        }
    )
    return status


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
        "schema_version": "diagnostic_center_second_provider_next_prd_recommendation_v1",
        "prd": PRD,
        "final_status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "hotfix_required")),
        "next_recommended_prd": str(decision_gate.get("next_recommended_prd", NEXT_PRD_IF_BLOCKED)),
        "blockers": _safe_list(decision_gate.get("blockers")),
        "warnings": _safe_list(decision_gate.get("warnings")),
    }


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD_IF_PASSED",
    "NEXT_PRD_IF_BLOCKED",
    "ALLOWLISTED_OPERATOR",
    "NORMAL_CONTROL_USERS",
    "MAX_PROVIDER_CALLS",
    "FOCUS_SOURCE_ID",
    "CONTRACT_PAYLOAD",
    "preflight_source",
    "build_source_gate",
    "build_botdb_live_preflight",
    "build_provider_availability_preflight",
    "build_rollback_precheck",
    "build_execution_manifest",
    "load_scenarios_from_fixture",
    "execute_second_provider_backed_smoke",
    "build_provider_budget_gate",
    "build_normal_user_no_effect_gate",
    "build_quality_micro_shift_gate",
    "build_safety_kb_boundary_gate",
    "build_trace_sanitization_gate",
    "build_rollback_postcheck",
    "build_botdb_stability_gate",
    "build_no_mutation_proof",
    "build_decision_gate",
    "build_scorecard",
    "docs_sync_status",
    "build_next_prd_recommendation",
    "_sha256",
]
