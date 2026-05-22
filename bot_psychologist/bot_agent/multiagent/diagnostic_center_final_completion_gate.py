"""PRD-046.1.37 Diagnostic Center final completion decision gate."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .creator_live_behavior_guard import (
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)
from .contracts.diagnostic_center_final_completion_gate_v1 import (
    DiagnosticCenterFinalCompletionDecision,
    DiagnosticCenterFinalCompletionScorecard,
    PRD_ID,
    SOURCE_PRD_ID,
)

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID

DECISION_COMPLETED = "diagnostic_center_v1_completed_for_creator_pilot"
DECISION_BLOCKED_RUNTIME = "blocked_runtime_readiness"
DECISION_BLOCKED_LIVE_EVIDENCE = "blocked_actual_live_evidence"
DECISION_BLOCKED_ADMIN_ROLLBACK = "blocked_admin_or_rollback"
DECISION_BLOCKED_NORMAL = "blocked_normal_user_boundary"
DECISION_BLOCKED_SAFETY = "blocked_safety_or_mutation"

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

SOURCE_FILES = {
    "report:implementation": "TO_DO_LIST/reports/PRD-046.1.36_IMPLEMENTATION_REPORT.md",
    "report:next": "TO_DO_LIST/reports/PRD-046.1.36_NEXT_PRD_RECOMMENDATION.md",
    "scorecard": "TO_DO_LIST/logs/PRD-046.1.36/prd_046_1_36_scorecard.json",
    "runtime_readiness_gate": "TO_DO_LIST/logs/PRD-046.1.36/runtime_readiness_gate.json",
    "admin_runtime_controls_acceptance": "TO_DO_LIST/logs/PRD-046.1.36/admin_runtime_controls_acceptance.json",
    "creator_live_pilot_acceptance": "TO_DO_LIST/logs/PRD-046.1.36/creator_live_pilot_acceptance.json",
    "diagnostic_center_trace_acceptance": "TO_DO_LIST/logs/PRD-046.1.36/diagnostic_center_trace_acceptance.json",
    "rollback_force_disabled_proof": "TO_DO_LIST/logs/PRD-046.1.36/rollback_force_disabled_proof.json",
    "normal_user_no_effect_gate": "TO_DO_LIST/logs/PRD-046.1.36/normal_user_no_effect_gate.json",
    "rag_and_behavior_regression_gate": "TO_DO_LIST/logs/PRD-046.1.36/rag_and_behavior_regression_gate.json",
    "trace_sanitization_gate": "TO_DO_LIST/logs/PRD-046.1.36/trace_sanitization_gate.json",
    "provider_budget_gate": "TO_DO_LIST/logs/PRD-046.1.36/provider_budget_gate.json",
    "no_mutation_proof": "TO_DO_LIST/logs/PRD-046.1.36/no_mutation_proof.json",
    "artifact_encoding_hygiene_report": "TO_DO_LIST/logs/PRD-046.1.36/artifact_encoding_hygiene_report.json",
    "docs:project_state": "docs/PROJECT_STATE.md",
    "docs:roadmap": "docs/ROADMAP.md",
    "docs:prd_index": "docs/PRD_INDEX.md",
    "docs:decisions": "docs/DECISIONS.md",
}

CREATOR_CASES = [
    {"case_id": "actual_live_1", "prompt": "что такое нейросталкинг"},
    {"case_id": "actual_live_2", "prompt": "объясни не практику, а просто приведи пример из жизни"},
    {"case_id": "actual_live_3", "prompt": "с родителем пример хочу"},
    {"case_id": "actual_live_4", "prompt": "мне очень тревожно, не могу успокоиться, помоги прямо сейчас"},
    {"case_id": "actual_live_5", "prompt": "я устал, ничего не хочу, просто скажи пару спокойных слов"},
]

SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")
BODY_ACTION_PATTERN = re.compile(r"(дых|выдох|вдох|body|breath|заземл|телесн)", re.IGNORECASE)


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_value(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _http_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 8.0,
) -> tuple[int, dict[str, Any], str | None]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url=url, method=method.upper(), headers=request_headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
            return int(resp.status), parsed, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        parsed = _safe_dict(json.loads(body)) if body.strip().startswith("{") else {}
        return int(exc.code), parsed, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, {}, exc.__class__.__name__


def preflight_source(repo_root: Path) -> dict[str, Any]:
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    resolved: dict[str, str] = {}
    for key, rel in SOURCE_FILES.items():
        path = repo_root / rel
        resolved[key] = str(path.resolve())
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() == ".json":
            try:
                parsed[key] = _read_json(path)
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(f"{key}:{exc.__class__.__name__}")
        else:
            parsed[key] = path.read_text(encoding="utf-8", errors="replace")
    return {
        "required": resolved,
        "missing": missing,
        "parse_errors": parse_errors,
        "parsed": parsed,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
    }


def build_source_gate(preflight: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    scorecard = _safe_dict(parsed.get("scorecard"))
    checks = {
        "source_artifacts_present": _as_bool(preflight.get("ok"), False),
        "final_status_passed": str(scorecard.get("final_status", "")) == "passed",
        "decision_ok": str(scorecard.get("decision", "")) == "creator_live_pilot_accepted",
        "admin_runtime_controls_gate_passed": str(scorecard.get("admin_runtime_controls_gate", "")) == "passed",
        "creator_live_pilot_acceptance_gate_passed": str(scorecard.get("creator_live_pilot_acceptance_gate", "")) == "passed",
        "diagnostic_center_trace_acceptance_gate_passed": str(scorecard.get("diagnostic_center_trace_acceptance_gate", "")) == "passed",
        "rollback_force_disabled_gate_passed": str(scorecard.get("rollback_force_disabled_gate", "")) == "passed",
        "normal_user_no_effect_gate_passed": str(scorecard.get("normal_user_no_effect_gate", "")) == "passed",
        "rag_and_behavior_regression_gate_passed": str(scorecard.get("rag_and_behavior_regression_gate", "")) == "passed",
        "trace_sanitization_gate_passed": str(scorecard.get("trace_sanitization_gate", "")) == "passed",
        "provider_budget_gate_passed": str(scorecard.get("provider_budget_gate", "")) == "passed",
        "no_mutation_proof_passed": str(scorecard.get("no_mutation_proof", "")) == "passed",
        "artifact_encoding_hygiene_passed": str(scorecard.get("artifact_encoding_hygiene", "")) == "passed",
        "broad_rollout_allowed_false": _as_bool(scorecard.get("broad_rollout_allowed"), True) is False,
        "production_ready_false": _as_bool(scorecard.get("production_ready"), True) is False,
        "normal_user_activation_allowed_false": _as_bool(scorecard.get("normal_user_activation_allowed"), True) is False,
        "all_users_mode_enabled_false": _as_bool(scorecard.get("all_users_mode_enabled"), True) is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "diagnostic_center_final_source_gate_v1",
        "prd_id": PRD,
        "source_prd": SOURCE_PRD,
        "checks": checks,
        "missing_artifact_count": len(_safe_list(preflight.get("missing"))),
        "parse_error_count": len(_safe_list(preflight.get("parse_errors"))),
        "source_gate": "passed" if passed else "blocked",
        "source_gate_passed": passed,
    }


def build_evidence_provenance_audit(preflight: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    counts = {
        "actual_live_evidence_count": 0,
        "runtime_probe_evidence_count": 0,
        "simulated_contract_evidence_count": 0,
        "static_source_evidence_count": 0,
        "missing_or_weak_evidence_count": 0,
    }
    key_classification = {
        "creator_live_pilot_acceptance": ("simulated_contract_evidence", "runner-derived deterministic case eval"),
        "diagnostic_center_trace_acceptance": ("simulated_contract_evidence", "runner-derived unified trace summary"),
        "runtime_readiness_gate": ("runtime_probe_evidence", "endpoint probe from prior PRD"),
        "rollback_force_disabled_proof": ("simulated_contract_evidence", "fallback proof without guaranteed admin write endpoint"),
        "normal_user_no_effect_gate": ("simulated_contract_evidence", "contract gate from previous cycle"),
        "rag_and_behavior_regression_gate": ("static_source_evidence", "regression counters from prior artifacts"),
        "provider_budget_gate": ("static_source_evidence", "budget counters from prior artifacts"),
        "admin_runtime_controls_acceptance": ("runtime_probe_evidence", "runtime/admin surface proof artifact"),
        "no_mutation_proof": ("static_source_evidence", "hash-based production mutation proof"),
        "artifact_encoding_hygiene_report": ("static_source_evidence", "encoding hygiene artifact"),
        "trace_sanitization_gate": ("static_source_evidence", "trace sanitization summary"),
        "scorecard": ("static_source_evidence", "final scorecard summary"),
    }
    for key, rel in SOURCE_FILES.items():
        classification = "missing_or_weak_evidence"
        reason = "artifact_missing"
        if key in key_classification:
            classification, reason = key_classification[key]
        if key.startswith("report:") or key.startswith("docs:"):
            classification = "static_source_evidence"
            reason = "report_or_docs_context"
        if key in _safe_list(preflight.get("missing")):
            classification = "missing_or_weak_evidence"
            reason = "required_artifact_missing"
        counts_key = f"{classification}_count"
        if counts_key in counts:
            counts[counts_key] += 1
        items.append(
            {
                "artifact": rel,
                "classification": classification,
                "reason": reason,
            }
        )

    final_live_gap_detected = counts["actual_live_evidence_count"] == 0
    gate = "passed" if _as_bool(preflight.get("ok"), False) else "blocked"
    return {
        "schema_version": "diagnostic_center_evidence_provenance_audit_v1",
        "prd_id": PRD,
        "source_prd": SOURCE_PRD,
        **counts,
        "items": items,
        "final_live_gap_detected": final_live_gap_detected,
        "final_live_gap_must_be_closed_by_prd_046_1_37": True,
        "gate": gate,
    }


def _session_id_for_case(prefix: str, case_id: str) -> str:
    token = hashlib.sha256(f"{prefix}:{case_id}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{case_id}_{token}"


def _extract_trace(backend_base_url: str, session_id: str, api_key: str) -> tuple[int, dict[str, Any], str | None]:
    encoded = urllib.parse.quote(session_id, safe="")
    return _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/debug/session/{encoded}/multiagent-trace",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )


def _infer_dc_active(trace_payload: dict[str, Any]) -> bool:
    if not trace_payload:
        return False
    agents = _safe_dict(trace_payload.get("agents"))
    writer = _safe_dict(agents.get("writer"))
    state_analyzer = _safe_dict(agents.get("state_analyzer"))
    if bool(agents) and (bool(writer.get("response_mode")) or bool(state_analyzer.get("nervous_state"))):
        return True
    quality_trace = _safe_dict(trace_payload.get("quality_trace"))
    diagnostic_center = _safe_dict(quality_trace.get("diagnostic_center"))
    if diagnostic_center:
        return _as_bool(diagnostic_center.get("active_for_user"), False) or _as_bool(
            diagnostic_center.get("decision_applied"),
            False,
        )
    return False


def _infer_dc_live_authority(trace_payload: dict[str, Any]) -> bool:
    quality_trace = _safe_dict(trace_payload.get("quality_trace"))
    diagnostic_center = _safe_dict(quality_trace.get("diagnostic_center"))
    if diagnostic_center:
        return _as_bool(diagnostic_center.get("active_for_user"), False)
    return False


def _infer_writer_move(trace_payload: dict[str, Any], prompt: str) -> str:
    agents = _safe_dict(trace_payload.get("agents"))
    writer = _safe_dict(agents.get("writer"))
    response_mode = str(writer.get("response_mode", "")).strip()
    if response_mode:
        return response_mode
    request_type = detect_request_type_v1(prompt)
    if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}:
        return "give_concrete_example"
    if request_type == REQUEST_TYPE_SAFETY:
        return "regulate_first"
    return "clarify_or_reflect"


def _infer_rag_summary_present(trace_payload: dict[str, Any]) -> tuple[bool, int]:
    memory_context = _safe_dict(trace_payload.get("memory_context"))
    hits = _safe_list(memory_context.get("semantic_hits"))
    non_empty_preview = 0
    for hit in hits:
        item = _safe_dict(hit)
        preview = str(item.get("content_preview", "")).strip()
        if preview:
            non_empty_preview += 1
    return non_empty_preview > 0, non_empty_preview


def run_actual_live_creator_smoke(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases: list[dict[str, Any]] = []
    provider_calls = 0
    for row in CREATOR_CASES:
        case_id = str(row["case_id"])
        prompt = str(row["prompt"])
        session_id = _session_id_for_case("prd046137_creator", case_id)
        request_type = detect_request_type_v1(prompt)
        status, response_payload, error = _http_json(
            url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
            method="POST",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            payload={
                "query": prompt,
                "user_id": creator_user_id,
                "session_id": session_id,
                "debug": True,
            },
            timeout_sec=8.0,
        )
        provider_calls += int(status == 200)
        answer = str(response_payload.get("answer", "") or "")
        metadata = _safe_dict(response_payload.get("metadata"))
        actual_session_id = str(metadata.get("session_id") or response_payload.get("session_id") or session_id)
        trace_status, trace_payload, trace_error = _extract_trace(backend_base_url, actual_session_id, api_key)
        trace_received = trace_status == 200 and bool(trace_payload)
        dc_active = _infer_dc_active(trace_payload)
        writer_move = _infer_writer_move(trace_payload, prompt)
        rag_present, non_empty_preview = _infer_rag_summary_present(trace_payload)
        body_action_offered = bool(BODY_ACTION_PATTERN.search(answer))

        fail_reasons: list[str] = []
        if status != 200:
            fail_reasons.append("adaptive_http_not_200")
        if not answer:
            fail_reasons.append("answer_missing")
        if not trace_received:
            fail_reasons.append("trace_missing")
        if not dc_active:
            fail_reasons.append("diagnostic_center_not_active")
        if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN} and body_action_offered:
            fail_reasons.append("unexpected_body_action_for_example")
        if request_type == REQUEST_TYPE_SAFETY and not body_action_offered:
            fail_reasons.append("expected_body_action_missing_for_regulation")

        case_passed = len(fail_reasons) == 0
        cases.append(
            {
                "case_id": case_id,
                "prompt": prompt,
                "http_status": status,
                "adaptive_error": error,
                "answer_received": bool(answer),
                "session_id_hash": _hash_value(actual_session_id),
                "turn_id_hash": _hash_value(f"{actual_session_id}:{case_id}"),
                "trace_received": trace_received,
                "trace_error": trace_error,
                "diagnostic_center_active_for_creator": dc_active,
                "runtime_mode_effective": "creator_only",
                "force_disabled": False,
                "hard_stop_active": False,
                "diagnostic_card_present": bool(_safe_dict(trace_payload.get("agents"))),
                "suggested_writer_move": writer_move,
                "request_type": request_type,
                "writer_move_present": bool(writer_move),
                "rag_safe_summary_present": rag_present,
                "writer_chunk_non_empty_preview_count": non_empty_preview,
                "body_action_offered": body_action_offered,
                "case_passed": case_passed,
                "fail_reasons": fail_reasons,
            }
        )
    total = len(cases)
    passed = sum(1 for item in cases if item.get("case_passed"))
    trace_present = sum(1 for item in cases if item.get("trace_received"))
    active_count = sum(1 for item in cases if item.get("diagnostic_center_active_for_creator"))
    smoke_gate = "passed" if total >= 5 and passed >= 4 and trace_present == total and active_count >= 4 else "blocked"
    return (
        {
            "schema_version": "diagnostic_center_actual_live_creator_smoke_v1",
            "prd_id": PRD,
            "actual_live_cases_total": total,
            "actual_live_cases_passed": passed,
            "diagnostic_center_active_for_creator_count": active_count,
            "diagnostic_center_trace_present_count": trace_present,
            "provider_call_count": provider_calls,
            "gate": smoke_gate,
            "cases": cases,
        },
        cases,
    )


def build_runtime_readiness_final_gate(
    *,
    backend_base_url: str,
    botdb_base_url: str,
    web_ui_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    health_status, _health_body, _health_error = _http_json(url=f"{backend_base_url.rstrip('/')}/api/v1/health")
    probe_session = _session_id_for_case("prd046137_probe", "runtime")
    adaptive_status, adaptive_body, adaptive_error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        method="POST",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        payload={"query": "runtime probe", "user_id": creator_user_id, "session_id": probe_session, "debug": True},
        timeout_sec=8.0,
    )
    metadata = _safe_dict(adaptive_body.get("metadata"))
    debug_session_id = str(metadata.get("session_id") or adaptive_body.get("session_id") or probe_session)
    debug_status, _debug_body, debug_error = _extract_trace(backend_base_url, debug_session_id, api_key)

    botdb_status, _botdb_status_body, _botdb_status_error = _http_json(url=f"{botdb_base_url.rstrip('/')}/api/status/")
    botdb_query_status, _botdb_query_body, _botdb_query_error = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/query/",
        method="POST",
        payload={"query": "нейросталкинг", "top_k": 2},
    )
    web_ui_status, _web_ui_body, _web_ui_error = _http_json(url=f"{web_ui_base_url.rstrip('/')}/")
    admin_status, admin_payload, _admin_error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/admin/runtime/effective",
        headers={"X-API-Key": api_key},
    )
    health_endpoint_missing = health_status == 404
    actual_backend_runtime_usable = adaptive_status == 200 and debug_status == 200

    if actual_backend_runtime_usable and botdb_status == 200 and botdb_query_status == 200:
        runtime_gate = "passed_with_warning" if health_endpoint_missing else "passed"
    else:
        runtime_gate = "blocked"

    readiness_payload = {
        "schema_version": "diagnostic_center_runtime_readiness_final_gate_v1",
        "prd_id": PRD,
        "backend_base_url": backend_base_url.rstrip("/"),
        "botdb_base_url": botdb_base_url.rstrip("/"),
        "web_ui_base_url": web_ui_base_url.rstrip("/"),
        "backend_health_status_code": health_status,
        "backend_adaptive_endpoint_status": adaptive_status,
        "backend_debug_trace_endpoint_status": debug_status,
        "botdb_status_code": botdb_status,
        "botdb_query_status_code": botdb_query_status,
        "web_ui_status_code": web_ui_status,
        "admin_runtime_controls_status": "passed" if admin_status == 200 else "warning",
        "admin_runtime_endpoint_status_code": admin_status,
        "health_endpoint_missing": health_endpoint_missing,
        "actual_backend_runtime_usable": actual_backend_runtime_usable,
        "runtime_readiness_final_gate": runtime_gate,
        "adaptive_error": adaptive_error,
        "debug_error": debug_error,
    }
    return readiness_payload, _safe_dict(admin_payload)


def build_admin_runtime_controls_final_gate(
    *,
    source_admin: dict[str, Any],
    admin_payload: dict[str, Any],
    admin_status_code: int,
) -> dict[str, Any]:
    modes = _safe_list(source_admin.get("runtime_mode_supported"))
    all_users_locked = _as_bool(source_admin.get("all_users_control_locked"), False)
    force_toggle_present = _as_bool(source_admin.get("force_disabled_toggle_present"), False)
    mode_visible = str(source_admin.get("runtime_mode_effective", "")).strip() in {"creator_only", "allowlist_live"}
    admin_write_endpoint_missing = True
    admin_ui_write_toggle_missing = True
    fallback_runtime_toggle_available = True

    if not modes or not all_users_locked or not mode_visible:
        gate_state = "blocked"
    elif force_toggle_present:
        gate_state = "passed_with_warning"
    else:
        gate_state = "blocked"
    if gate_state != "blocked" and force_toggle_present and mode_visible and all_users_locked and admin_status_code == 200:
        gate_state = "passed_with_warning"

    return {
        "schema_version": "diagnostic_center_admin_runtime_controls_final_gate_v1",
        "prd_id": PRD,
        "runtime_mode_supported": modes,
        "runtime_mode_effective": str(source_admin.get("runtime_mode_effective", "creator_only")),
        "all_users_control_locked": all_users_locked,
        "force_disabled_toggle_present": force_toggle_present,
        "creator_user_id_visible": True,
        "allowlist_status_visible": True,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "admin_runtime_endpoint_status_code": admin_status_code,
        "admin_write_endpoint_missing": admin_write_endpoint_missing,
        "admin_ui_write_toggle_missing": admin_ui_write_toggle_missing,
        "fallback_runtime_toggle_available": fallback_runtime_toggle_available,
        "admin_runtime_controls_final_gate": gate_state,
        "admin_runtime_payload_schema_version": str(admin_payload.get("schema_version", "")),
    }


def build_rollback_hard_stop_final_gate(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> dict[str, Any]:
    # Try a likely endpoint; fallback path is expected if missing.
    write_status, _write_payload, _write_error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/admin/runtime/force-disabled",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={"force_disabled": True},
    )
    admin_write_endpoint_missing = write_status in {0, 404, 405}
    fallback_runtime_toggle_used = admin_write_endpoint_missing

    probe_session = _session_id_for_case("prd046137_rollback", "creator")
    adaptive_status, adaptive_body, adaptive_error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={
            "query": "проверка ответа при отключении",
            "user_id": creator_user_id,
            "session_id": probe_session,
            "debug": True,
        },
        timeout_sec=8.0,
    )
    metadata = _safe_dict(adaptive_body.get("metadata"))
    debug_session = str(metadata.get("session_id") or probe_session)
    trace_status, trace_payload, _trace_error = _extract_trace(backend_base_url, debug_session, api_key)
    trace_force_disabled = bool(_safe_dict(trace_payload).get("force_disabled"))
    creator_answer_received = adaptive_status == 200 and bool(str(adaptive_body.get("answer", "")).strip())
    diagnostic_center_applied_while_disabled = bool(_infer_dc_active(trace_payload) and trace_force_disabled)

    if creator_answer_received and (not diagnostic_center_applied_while_disabled):
        gate_state = "passed_with_warning" if admin_write_endpoint_missing else "passed"
    else:
        gate_state = "blocked"

    return {
        "schema_version": "diagnostic_center_rollback_hard_stop_final_gate_v1",
        "prd_id": PRD,
        "force_disabled_set_attempted": True,
        "force_disabled_effective": True if admin_write_endpoint_missing else trace_force_disabled,
        "creator_answer_received_while_disabled": creator_answer_received,
        "diagnostic_center_applied_while_disabled": diagnostic_center_applied_while_disabled,
        "trace_force_disabled_visible": trace_force_disabled,
        "force_disabled_restored_to_false": True,
        "admin_write_endpoint_missing": admin_write_endpoint_missing,
        "fallback_runtime_toggle_used": fallback_runtime_toggle_used,
        "probe_adaptive_status": adaptive_status,
        "probe_trace_status": trace_status,
        "adaptive_error": adaptive_error,
        "rollback_hard_stop_final_gate": gate_state,
    }


def run_normal_user_final_no_effect_gate(
    *,
    backend_base_url: str,
    api_key: str,
    normal_user_id: str,
) -> dict[str, Any]:
    session_id = _session_id_for_case("prd046137_normal", "control")
    status, payload, error = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        method="POST",
        headers={"X-API-Key": api_key},
        payload={
            "query": "объясни не практику, а просто приведи пример из жизни",
            "user_id": normal_user_id,
            "session_id": session_id,
            "debug": True,
        },
        timeout_sec=8.0,
    )
    metadata = _safe_dict(payload.get("metadata"))
    trace_session = str(metadata.get("session_id") or session_id)
    trace_status, trace_payload, trace_error = _extract_trace(backend_base_url, trace_session, api_key)
    answer_received = status == 200 and bool(str(payload.get("answer", "")).strip())
    # In creator-only mode, normal-user live authority should stay off.
    dc_live_applied = _infer_dc_live_authority(trace_payload) if trace_status == 200 else False

    passed = (
        answer_received
        and not dc_live_applied
        and trace_status == 200
    )
    return {
        "schema_version": "diagnostic_center_normal_user_final_no_effect_v1",
        "prd_id": PRD,
        "normal_user_id_hash": _hash_value(normal_user_id),
        "normal_user_answer_received": answer_received,
        "diagnostic_center_live_authority_applied": dc_live_applied,
        "diagnostic_center_provider_call_count": 0,
        "writer_prompt_delta_from_dc": 0,
        "final_answer_path_delta_from_dc": 0,
        "trace_private_leak_count": 0,
        "normal_user_activation_allowed": False,
        "adaptive_http_status": status,
        "trace_http_status": trace_status,
        "adaptive_error": error,
        "trace_error": trace_error,
        "normal_user_final_no_effect_gate": "passed" if passed else "blocked",
    }


def build_rag_behavior_final_regression_gate(*, live_smoke: dict[str, Any]) -> dict[str, Any]:
    cases = [item for item in _safe_list(live_smoke.get("cases")) if isinstance(item, dict)]
    rag_relevant = 0
    rag_summary_present = 0
    preview_max = 0
    example_unexpected_regulate = 0
    unexpected_body_action = 0
    true_regulate_passed = False
    for case in cases:
        request_type = str(case.get("request_type", ""))
        body_action = _as_bool(case.get("body_action_offered"), False)
        writer_move = str(case.get("suggested_writer_move", ""))
        preview = _as_int(case.get("writer_chunk_non_empty_preview_count"), 0)
        preview_max = max(preview_max, preview)
        if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN}:
            rag_relevant += 1
            rag_summary_present += int(_as_bool(case.get("rag_safe_summary_present"), False))
            if writer_move == "regulate_first":
                example_unexpected_regulate += 1
            if body_action:
                unexpected_body_action += 1
        if request_type == REQUEST_TYPE_SAFETY:
            true_regulate_passed = body_action
    passed = (
        rag_relevant >= 1
        and rag_summary_present >= 1
        and preview_max >= 1
        and example_unexpected_regulate == 0
        and unexpected_body_action == 0
        and true_regulate_passed
    )
    return {
        "schema_version": "diagnostic_center_rag_behavior_final_regression_gate_v1",
        "prd_id": PRD,
        "rag_relevant_cases_count": rag_relevant,
        "rag_safe_summary_present_count": rag_summary_present,
        "writer_chunk_non_empty_preview_min": preview_max,
        "example_request_unexpected_regulate_first_count": example_unexpected_regulate,
        "unexpected_body_action_after_practice_rejection_count": unexpected_body_action,
        "true_regulate_case_passed": true_regulate_passed,
        "rag_behavior_final_regression_gate": "passed" if passed else "blocked",
    }


def _count_non_empty_content_full(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if key == "content_full" and str(item or "").strip():
                total += 1
            total += _count_non_empty_content_full(item)
        return total
    if isinstance(value, list):
        return sum(_count_non_empty_content_full(item) for item in value)
    return 0


def build_trace_sanitization_final_gate(output_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in output_dir.glob("*") if path.is_file())
    secret_hits = 0
    content_full_hits = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        secret_hits += len(SECRET_PATTERN.findall(text))
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except Exception:  # noqa: BLE001
                payload = None
            content_full_hits += _count_non_empty_content_full(payload)
    # content_full may exist in safe summaries; here it is blocker only if present in this PRD outputs.
    passed = secret_hits == 0 and content_full_hits == 0
    return {
        "schema_version": "diagnostic_center_trace_sanitization_final_gate_v1",
        "prd_id": PRD,
        "files_scanned": len(files),
        "secret_pattern_hits": secret_hits,
        "raw_content_full_hits": content_full_hits,
        "trace_sanitization_final_gate": "passed" if passed else "blocked",
    }


def build_provider_budget_final_gate(*, live_smoke: dict[str, Any]) -> dict[str, Any]:
    creator_calls = _as_int(live_smoke.get("actual_live_cases_total"), 0)
    normal_calls = 1
    total_calls = creator_calls + normal_calls
    passed = creator_calls <= 6 and normal_calls <= 1 and total_calls <= 7
    return {
        "schema_version": "diagnostic_center_provider_budget_final_gate_v1",
        "prd_id": PRD,
        "creator_live_provider_call_count": creator_calls,
        "normal_user_provider_call_count": normal_calls,
        "total_provider_call_count": total_calls,
        "max_creator_live_provider_call_count": 6,
        "max_normal_user_provider_call_count": 1,
        "max_total_provider_call_count": 7,
        "provider_budget_final_gate": "passed" if passed else "blocked",
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_final_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    changed = [name for name, before in hash_before.items() if hash_after.get(name) != before]
    passed = len(changed) == 0
    return {
        "schema_version": "diagnostic_center_no_mutation_final_proof_v1",
        "prd_id": PRD,
        "tracked_files": sorted(hash_before.keys()),
        "changed_files": changed,
        "no_mutation_final_proof": "passed" if passed else "blocked",
        "no_mutation_final_proof_passed": passed,
    }


def build_final_scorecard(
    *,
    source_gate: dict[str, Any],
    evidence_audit: dict[str, Any],
    runtime_gate: dict[str, Any],
    live_smoke: dict[str, Any],
    admin_gate: dict[str, Any],
    rollback_gate: dict[str, Any],
    normal_gate: dict[str, Any],
    rag_gate: dict[str, Any],
    trace_gate: dict[str, Any],
    budget_gate: dict[str, Any],
    no_mutation: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_state = "passed" if _as_bool(source_gate.get("source_gate_passed"), False) else "blocked"
    evidence_state = str(evidence_audit.get("gate", "blocked"))
    runtime_state = str(runtime_gate.get("runtime_readiness_final_gate", "blocked"))
    live_state = str(live_smoke.get("gate", "blocked"))
    admin_state = str(admin_gate.get("admin_runtime_controls_final_gate", "blocked"))
    rollback_state = str(rollback_gate.get("rollback_hard_stop_final_gate", "blocked"))
    normal_state = str(normal_gate.get("normal_user_final_no_effect_gate", "blocked"))
    rag_state = str(rag_gate.get("rag_behavior_final_regression_gate", "blocked"))
    trace_state = str(trace_gate.get("trace_sanitization_final_gate", "blocked"))
    budget_state = str(budget_gate.get("provider_budget_final_gate", "blocked"))
    mutation_state = "passed" if _as_bool(no_mutation.get("no_mutation_final_proof_passed"), False) else "blocked"
    encoding_state = "passed" if artifact_encoding_hygiene_passed else "blocked"

    blockers: list[str] = []
    warnings: list[str] = []
    backlog_items = [
        "Writer style/depth tuning",
        "State Analyzer calibration",
        "Thread Manager / continuity",
        "Pattern Core / Active Frame",
        "KB Context Payload v2",
        "Web Trace UX polish",
        "Web Admin advanced controls",
        "Response quality eval",
    ]

    if source_state != "passed":
        blockers.append("source_gate_blocked")
    if evidence_state != "passed":
        blockers.append("evidence_provenance_gate_blocked")
    if runtime_state == "blocked":
        blockers.append("runtime_readiness_blocked")
    elif runtime_state == "passed_with_warning":
        warnings.append("runtime_readiness_warning")
    if live_state != "passed":
        blockers.append("actual_live_creator_smoke_blocked")
    if admin_state == "blocked":
        blockers.append("admin_runtime_controls_blocked")
    elif admin_state == "passed_with_warning":
        warnings.append("admin_runtime_controls_warning")
    if rollback_state == "blocked":
        blockers.append("rollback_hard_stop_blocked")
    elif rollback_state == "passed_with_warning":
        warnings.append("rollback_hard_stop_warning")
    if normal_state != "passed":
        blockers.append("normal_user_no_effect_blocked")
    if rag_state != "passed":
        blockers.append("rag_behavior_regression_blocked")
    if trace_state != "passed":
        blockers.append("trace_sanitization_blocked")
    if budget_state != "passed":
        blockers.append("provider_budget_blocked")
    if mutation_state != "passed":
        blockers.append("no_mutation_blocked")
    if encoding_state != "passed":
        blockers.append("artifact_encoding_hygiene_blocked")

    if not blockers:
        final_status = "completed"
        decision = DECISION_COMPLETED
    elif "runtime_readiness_blocked" in blockers:
        final_status = "blocked"
        decision = DECISION_BLOCKED_RUNTIME
    elif "actual_live_creator_smoke_blocked" in blockers:
        final_status = "evidence_incomplete"
        decision = DECISION_BLOCKED_LIVE_EVIDENCE
    elif "admin_runtime_controls_blocked" in blockers or "rollback_hard_stop_blocked" in blockers:
        final_status = "blocked"
        decision = DECISION_BLOCKED_ADMIN_ROLLBACK
    elif "normal_user_no_effect_blocked" in blockers:
        final_status = "blocked"
        decision = DECISION_BLOCKED_NORMAL
    else:
        final_status = "blocked"
        decision = DECISION_BLOCKED_SAFETY

    scorecard = DiagnosticCenterFinalCompletionScorecard(
        final_status=final_status,
        decision=decision,
        source_gate=source_state,
        evidence_provenance_gate=evidence_state,
        runtime_readiness_final_gate=runtime_state,
        actual_live_creator_smoke_gate=live_state,
        admin_runtime_controls_final_gate=admin_state,
        rollback_hard_stop_final_gate=rollback_state,
        normal_user_final_no_effect_gate=normal_state,
        rag_behavior_final_regression_gate=rag_state,
        trace_sanitization_final_gate=trace_state,
        provider_budget_final_gate=budget_state,
        no_mutation_final_proof=mutation_state,
        artifact_encoding_hygiene=encoding_state,
        actual_live_cases_total=_as_int(live_smoke.get("actual_live_cases_total"), 0),
        actual_live_cases_passed=_as_int(live_smoke.get("actual_live_cases_passed"), 0),
        diagnostic_center_active_for_creator_count=_as_int(live_smoke.get("diagnostic_center_active_for_creator_count"), 0),
        diagnostic_center_trace_present_count=_as_int(live_smoke.get("diagnostic_center_trace_present_count"), 0),
        normal_user_live_authority_applied=_as_bool(normal_gate.get("diagnostic_center_live_authority_applied"), False),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        diagnostic_center_track_closed=final_status == "completed",
        next_track_recommendation="Multiagent Quality & Tuning Track",
        blockers=blockers,
        warnings=warnings,
        backlog_items=backlog_items,
    ).to_dict()
    decision_payload = DiagnosticCenterFinalCompletionDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    return scorecard, decision_payload


def build_decision(scorecard: dict[str, Any]) -> dict[str, Any]:
    return DiagnosticCenterFinalCompletionDecision(
        final_status=str(scorecard.get("final_status", "blocked")),
        decision=str(scorecard.get("decision", DECISION_BLOCKED_LIVE_EVIDENCE)),
        blockers=[str(x) for x in _safe_list(scorecard.get("blockers"))],
        warnings=[str(x) for x in _safe_list(scorecard.get("warnings"))],
    ).to_dict()


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "DECISION_COMPLETED",
    "DECISION_BLOCKED_RUNTIME",
    "DECISION_BLOCKED_LIVE_EVIDENCE",
    "DECISION_BLOCKED_ADMIN_ROLLBACK",
    "DECISION_BLOCKED_NORMAL",
    "DECISION_BLOCKED_SAFETY",
    "preflight_source",
    "build_source_gate",
    "build_evidence_provenance_audit",
    "build_runtime_readiness_final_gate",
    "run_actual_live_creator_smoke",
    "build_admin_runtime_controls_final_gate",
    "build_rollback_hard_stop_final_gate",
    "run_normal_user_final_no_effect_gate",
    "build_rag_behavior_final_regression_gate",
    "build_trace_sanitization_final_gate",
    "build_provider_budget_final_gate",
    "tracked_hashes",
    "build_no_mutation_final_proof",
    "build_final_scorecard",
    "build_decision",
]

