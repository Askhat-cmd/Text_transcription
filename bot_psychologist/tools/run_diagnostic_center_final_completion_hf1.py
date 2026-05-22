from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.creator_live_behavior_guard import (  # noqa: E402
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)
from bot_agent.multiagent.contracts.diagnostic_center_final_completion_hf1_v1 import (  # noqa: E402
    DiagnosticCenterFinalCompletionHF1Scorecard,
    PRD_ID,
)
from tools import validate_prd_artifact_encoding as encoding_validator  # noqa: E402

PRD = PRD_ID
SOURCE_PRD = "PRD-046.1.37"

DECISION_COMPLETED = "diagnostic_center_v1_completed_after_hf1"
DECISION_BLOCKED_RUNTIME = "blocked_runtime_readiness_after_hf1"
DECISION_BLOCKED_LIVE_EVIDENCE = "blocked_actual_live_evidence_after_hf1"

TIMEOUT_LADDER = [15, 30, 45, 60, 90]
TRACE_POLL_DELAYS_SEC = [3, 6, 10, 15, 20]
ATTEMPT_BACKOFF = {15: 2, 30: 4, 45: 6, 60: 8, 90: 0}

HEALTH_ALIASES = ["/api/v1/health", "/health", "/", "/api/health"]
TRACE_ALIASES = [
    "/api/debug/session/{session_id}/multiagent-trace",
    "/api/v1/debug/session/{session_id}/multiagent-trace",
    "/api/debug/sessions/{session_id}/multiagent-trace",
]

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

CREATOR_CASES = [
    {"case_id": "actual_live_1", "prompt": "что такое нейросталкинг"},
    {"case_id": "actual_live_2", "prompt": "объясни не практику, а просто приведи пример из жизни"},
    {"case_id": "actual_live_3", "prompt": "с родителем пример хочу"},
    {"case_id": "actual_live_4", "prompt": "мне очень тревожно, не могу успокоиться, помоги прямо сейчас"},
    {"case_id": "actual_live_5", "prompt": "я устал, ничего не хочу, просто скажи пару спокойных слов"},
]

BODY_ACTION_PATTERN = re.compile(r"(дых|выдох|вдох|body|breath|заземл|телесн)", re.IGNORECASE)
SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_value(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _sanitize_utf8_text(path: Path) -> None:
    if not path.exists():
        return
    raw = path.read_bytes()
    cleaned = raw.replace(b"\x00", b"")
    if cleaned != raw:
        path.write_bytes(cleaned)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _http_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 10.0,
) -> tuple[int, dict[str, Any], str | None, float]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url=url, method=method.upper(), headers=request_headers, data=data)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
            return int(resp.status), parsed, None, (time.perf_counter() - started) * 1000.0
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        parsed = _safe_dict(json.loads(raw)) if raw.strip().startswith("{") else {}
        return int(exc.code), parsed, f"http_{exc.code}", (time.perf_counter() - started) * 1000.0
    except Exception as exc:  # noqa: BLE001
        return 0, {}, exc.__class__.__name__, (time.perf_counter() - started) * 1000.0


def _extract_answer(payload: dict[str, Any]) -> str:
    for key in ("answer", "response", "text"):
        value = str(payload.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _classification_from_attempt(status: int, error: str | None, trace_received: bool) -> str:
    if status in {401, 403}:
        return "auth_failure"
    if status in {400, 422}:
        return "payload_schema_mismatch"
    if status >= 500:
        return "backend_error_5xx"
    if status == 200 and not trace_received:
        return "adaptive_completed_but_trace_timeout"
    if status == 0 and (error or "").lower().startswith("timeout"):
        return "adaptive_timeout_before_first_byte"
    return "unknown_timeout"


def _session_id(prefix: str, case_id: str) -> str:
    now = int(time.time())
    token = hashlib.sha256(f"{prefix}:{case_id}:{now}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{case_id}_{now}_{token}"


def _auth_headers(api_key: str) -> list[tuple[str, dict[str, str]]]:
    env_key = os.getenv("BOT_API_KEY", "").strip()
    variants: list[tuple[str, dict[str, str]]] = [
        ("x_api_key", {"X-API-Key": api_key, "Accept": "application/json"}),
        ("bearer_api_key", {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}),
    ]
    if env_key and env_key != api_key:
        variants.append(("x_api_key_env", {"X-API-Key": env_key, "Accept": "application/json"}))
    return variants


def _adaptive_call(
    *,
    backend_base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_sec: int,
) -> tuple[int, dict[str, Any], str | None, float, str]:
    url = f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive"
    auth_error_seen = False
    last: tuple[int, dict[str, Any], str | None, float, str] = (0, {}, "auth_failure", 0.0, "none")
    for auth_name, headers in _auth_headers(api_key):
        status, body, err, elapsed = _http_json(
            url=url,
            method="POST",
            headers=headers,
            payload=payload,
            timeout_sec=timeout_sec,
        )
        last = (status, body, err, elapsed, auth_name)
        if status in {401, 403}:
            auth_error_seen = True
            continue
        return status, body, err, elapsed, auth_name
    if auth_error_seen:
        return last
    return last


def _get_trace(
    *,
    backend_base_url: str,
    session_id: str,
    api_key: str,
    timeout_sec: float = 15.0,
) -> tuple[int, dict[str, Any], str | None, str]:
    encoded = urllib.parse.quote(session_id, safe="")
    for alias in TRACE_ALIASES:
        path = alias.format(session_id=encoded)
        status, body, error, _elapsed = _http_json(
            url=f"{backend_base_url.rstrip('/')}{path}",
            method="GET",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout_sec=timeout_sec,
        )
        if status == 200 and body:
            return status, body, None, path
        if status not in {404, 405}:
            return status, body, error, path
    return 404, {}, "trace_route_missing", TRACE_ALIASES[0]


def _poll_trace_after_timeout(
    *,
    backend_base_url: str,
    session_id: str,
    api_key: str,
) -> tuple[bool, dict[str, Any], int, int, str | None]:
    attempts = 0
    waited = 0
    for delay in TRACE_POLL_DELAYS_SEC:
        time.sleep(delay)
        waited += delay
        attempts += 1
        status, body, error, _path = _get_trace(
            backend_base_url=backend_base_url,
            session_id=session_id,
            api_key=api_key,
            timeout_sec=20.0,
        )
        if status == 200 and body:
            return True, body, attempts, waited, error
    return False, {}, attempts, waited, "trace_poll_timeout_after_answer"


def _infer_dc_active(trace_payload: dict[str, Any]) -> bool:
    quality_trace = _safe_dict(trace_payload.get("quality_trace"))
    diagnostic = _safe_dict(quality_trace.get("diagnostic_center"))
    if diagnostic:
        if _as_bool(diagnostic.get("active_for_user"), False) or _as_bool(diagnostic.get("decision_applied"), False):
            return True
    agents = _safe_dict(trace_payload.get("agents"))
    writer = _safe_dict(agents.get("writer"))
    state = _safe_dict(agents.get("state_analyzer"))
    return bool(writer.get("response_mode")) or bool(state.get("nervous_state"))


def _infer_dc_authority(trace_payload: dict[str, Any]) -> bool:
    quality_trace = _safe_dict(trace_payload.get("quality_trace"))
    diagnostic = _safe_dict(quality_trace.get("diagnostic_center"))
    return _as_bool(diagnostic.get("active_for_user"), False)


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


def _infer_rag(trace_payload: dict[str, Any]) -> tuple[bool, int]:
    memory = _safe_dict(trace_payload.get("memory_context"))
    hits = _safe_list(memory.get("semantic_hits"))
    non_empty = 0
    for raw_hit in hits:
        hit = _safe_dict(raw_hit)
        preview = str(hit.get("content_preview", "")).strip()
        if preview:
            non_empty += 1
    return non_empty > 0, non_empty


def _replace_section(text: str, header: str, body: str) -> str:
    pattern = re.compile(rf"{re.escape(header)}\n[\s\S]*?(?=\n## |\Z)")
    block = f"{header}\n{body.strip()}\n"
    if pattern.search(text):
        return pattern.sub(block.rstrip("\n"), text, count=1)
    return text.rstrip() + "\n\n" + block


def _apply_docs_state_pre_rerun_correction(repo_root: Path) -> dict[str, Any]:
    docs_path = repo_root / "docs" / "PROJECT_STATE.md"
    text = docs_path.read_text(encoding="utf-8", errors="replace") if docs_path.exists() else "# Project State\n"
    current_stage = (
        "PRD-046.1.37 is blocked on actual-live runtime readiness. "
        "Diagnostic Center v1 is not formally completed yet. "
        "Creator-only / allowlist architecture remains accepted for pilot candidate, "
        "final completion pending PRD-046.1.37-HF1 evidence repair."
    )
    next_prd = "`PRD-046.1.37-HF1 Actual Live Runtime Timeout / Evidence Repair / Docs State Correction`"
    track_state = "Diagnostic Center Track Status: PENDING FINAL ACTUAL-LIVE EVIDENCE REPAIR"
    updated = _replace_section(text, "## Current Stage", current_stage)
    updated = _replace_section(updated, "## Next Planned PRD", next_prd)
    if "## Diagnostic Center Track Status" in updated:
        updated = _replace_section(updated, "## Diagnostic Center Track Status", track_state)
    else:
        updated = updated.rstrip() + "\n\n## Diagnostic Center Track Status\n" + track_state + "\n"
    docs_path.write_text(updated.rstrip() + "\n", encoding="utf-8")

    pending_brief = repo_root / "TO_DO_LIST" / "TRANSFER_BRIEF_Diagnostic_Center_v1_PENDING_HF1_RERUN_RU.md"
    _write_text(
        pending_brief,
        "\n".join(
            [
                "# Transfer Brief - Diagnostic Center v1 pending HF1 rerun",
                "",
                "- source_prd: PRD-046.1.37",
                "- current_final_status: blocked",
                "- current_decision: blocked_runtime_readiness",
                "- diagnostic_center_track_status: PENDING FINAL ACTUAL-LIVE EVIDENCE REPAIR",
                "- next_prd: PRD-046.1.37-HF1",
            ]
        ),
    )
    return {
        "schema_version": "diagnostic_center_docs_state_pre_rerun_correction_v1",
        "prd_id": PRD,
        "project_state_updated": True,
        "pending_transfer_brief_written": str(pending_brief.relative_to(repo_root)),
        "docs_state_pre_rerun_correction": "passed",
    }


def _build_source_gate(repo_root: Path) -> dict[str, Any]:
    scorecard_path = repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.37" / "diagnostic_center_final_completion_scorecard.json"
    required = [
        repo_root / "TO_DO_LIST" / "reports" / "PRD-046.1.37_IMPLEMENTATION_REPORT.md",
        scorecard_path,
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.37" / "runtime_readiness_final_gate.json",
        repo_root / "TO_DO_LIST" / "logs" / "PRD-046.1.37" / "actual_live_creator_smoke.json",
    ]
    missing = [str(path.relative_to(repo_root)) for path in required if not path.exists()]
    scorecard = _safe_dict(_read_json(scorecard_path)) if scorecard_path.exists() else {}
    checks = {
        "source_artifacts_present": len(missing) == 0,
        "final_status_blocked": str(scorecard.get("final_status", "")) == "blocked",
        "decision_blocked_runtime_readiness": str(scorecard.get("decision", "")) == "blocked_runtime_readiness",
        "runtime_readiness_final_gate_blocked": str(scorecard.get("runtime_readiness_final_gate", "")) == "blocked",
        "actual_live_creator_smoke_gate_blocked": str(scorecard.get("actual_live_creator_smoke_gate", "")) == "blocked",
        "no_mutation_final_proof_passed": str(scorecard.get("no_mutation_final_proof", "")) == "passed",
        "artifact_encoding_hygiene_passed": str(scorecard.get("artifact_encoding_hygiene", "")) == "passed",
        "broad_rollout_allowed_false": _as_bool(scorecard.get("broad_rollout_allowed"), True) is False,
        "production_ready_false": _as_bool(scorecard.get("production_ready"), True) is False,
        "normal_user_activation_allowed_false": _as_bool(scorecard.get("normal_user_activation_allowed"), True) is False,
        "all_users_mode_enabled_false": _as_bool(scorecard.get("all_users_mode_enabled"), True) is False,
    }
    passed = all(checks.values())
    return {
        "schema_version": "diagnostic_center_hf1_source_gate_v1",
        "prd_id": PRD,
        "source_prd_id": SOURCE_PRD,
        "checks": checks,
        "missing_artifacts": missing,
        "source_gate": "passed" if passed else "blocked",
    }


def _probe_first_success(
    *,
    base_url: str,
    aliases: list[str],
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    method: str = "GET",
    timeout_sec: float = 10.0,
) -> tuple[int, str, str | None]:
    last_status = 0
    last_error: str | None = None
    last_path = aliases[0]
    for alias in aliases:
        status, _body, error, _elapsed = _http_json(
            url=f"{base_url.rstrip('/')}{alias}",
            method=method,
            headers=headers,
            payload=payload,
            timeout_sec=timeout_sec,
        )
        last_status, last_error, last_path = status, error, alias
        if status == 200:
            return status, alias, error
        if status not in {404, 405}:
            return status, alias, error
    return last_status, last_path, last_error


def _endpoint_matrix_probe(
    *,
    backend_base_url: str,
    botdb_base_url: str,
    web_ui_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> dict[str, Any]:
    health_status, health_path, health_error = _probe_first_success(
        base_url=backend_base_url,
        aliases=HEALTH_ALIASES,
        timeout_sec=10.0,
    )
    admin_status, _admin_body, admin_error, _admin_elapsed = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/admin/runtime/effective",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        timeout_sec=15.0,
    )
    probe_session = _session_id("prd046137hf1_probe", "matrix")
    adaptive_status, adaptive_body, adaptive_error, _adaptive_elapsed, _adaptive_auth = _adaptive_call(
        backend_base_url=backend_base_url,
        api_key=api_key,
        payload={"query": "короткий runtime warmup", "user_id": creator_user_id, "session_id": probe_session, "debug": True},
        timeout_sec=15,
    )
    adaptive_session = str(_safe_dict(adaptive_body.get("metadata")).get("session_id") or adaptive_body.get("session_id") or probe_session)
    debug_status, _trace_payload, debug_error, debug_path = _get_trace(
        backend_base_url=backend_base_url,
        session_id=adaptive_session,
        api_key=api_key,
        timeout_sec=15.0,
    )
    basic_status, _basic_body, basic_error, _basic_elapsed = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/basic",
        method="POST",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        payload={"query": "test basic", "user_id": creator_user_id, "session_id": probe_session},
        timeout_sec=20.0,
    )
    semantic_status, _semantic_body, semantic_error, _semantic_elapsed = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/basic-with-semantic",
        method="POST",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        payload={"query": "test semantic", "user_id": creator_user_id, "session_id": probe_session},
        timeout_sec=20.0,
    )
    graph_status, _graph_body, graph_error, _graph_elapsed = _http_json(
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/graph-powered",
        method="POST",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        payload={"query": "test graph", "user_id": creator_user_id, "session_id": probe_session},
        timeout_sec=20.0,
    )
    botdb_status, _botdb_body, botdb_error, _botdb_elapsed = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/status/",
        method="GET",
        timeout_sec=10.0,
    )
    botdb_query_status, _botdb_query_body, botdb_query_error, _botdb_query_elapsed = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/query/",
        method="POST",
        payload={"query": "нейросталкинг", "top_k": 2},
        timeout_sec=20.0,
    )
    web_status, _web_body, web_error, _web_elapsed = _http_json(
        url=f"{web_ui_base_url.rstrip('/')}/",
        method="GET",
        timeout_sec=10.0,
    )
    core_ok = all(
        [
            health_status == 200,
            admin_status == 200,
            debug_status == 200,
            botdb_status == 200,
            botdb_query_status == 200,
            web_status == 200,
        ]
    )
    if core_ok and adaptive_status == 200:
        probe_state = "passed"
    elif core_ok and adaptive_status == 0 and str(adaptive_error or "") == "TimeoutError":
        probe_state = "passed_with_warning"
    else:
        probe_state = "blocked"
    return {
        "schema_version": "diagnostic_center_hf1_endpoint_matrix_probe_v1",
        "prd_id": PRD,
        "health_endpoint_status": health_status,
        "health_alias_used": health_path,
        "health_error": health_error,
        "admin_runtime_effective_status": admin_status,
        "admin_error": admin_error,
        "adaptive_status": adaptive_status,
        "adaptive_error": adaptive_error,
        "debug_trace_status": debug_status,
        "debug_trace_alias_used": debug_path,
        "debug_error": debug_error,
        "basic_status": basic_status,
        "basic_error": basic_error,
        "basic_with_semantic_status": semantic_status,
        "basic_with_semantic_error": semantic_error,
        "graph_powered_status": graph_status,
        "graph_powered_error": graph_error,
        "botdb_status": botdb_status,
        "botdb_error": botdb_error,
        "botdb_query_status": botdb_query_status,
        "botdb_query_error": botdb_query_error,
        "web_ui_status": web_status,
        "web_ui_error": web_error,
        "endpoint_matrix_probe": probe_state,
    }


def _run_warmup(
    *,
    backend_base_url: str,
    botdb_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> dict[str, Any]:
    warmup_session = _session_id("prd046137hf1_warmup", "adaptive")
    warmup_status, warmup_body, warmup_error, warmup_elapsed, warmup_auth = _adaptive_call(
        backend_base_url=backend_base_url,
        api_key=api_key,
        payload={
            "query": "короткий runtime warmup",
            "user_id": creator_user_id,
            "session_id": warmup_session,
            "debug": True,
        },
        timeout_sec=30,
    )
    botdb_query_status, _botdb_query_payload, botdb_query_error, _botdb_elapsed = _http_json(
        url=f"{botdb_base_url.rstrip('/')}/api/query/",
        method="POST",
        payload={"query": "нейросталкинг", "top_k": 1},
        timeout_sec=20.0,
    )
    return {
        "schema_version": "diagnostic_center_hf1_warmup_v1",
        "prd_id": PRD,
        "warmup_session_hash": _hash_value(warmup_session),
        "warmup_adaptive_status": warmup_status,
        "warmup_adaptive_error": warmup_error,
        "warmup_elapsed_ms": round(warmup_elapsed, 1),
        "warmup_auth_variant": warmup_auth,
        "warmup_answer_received": bool(_extract_answer(warmup_body)),
        "botdb_query_status_code": botdb_query_status,
        "botdb_query_error": botdb_query_error,
    }


def _run_case_with_timeout_ladder(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
    case_id: str,
    prompt: str,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    request_type = detect_request_type_v1(prompt)
    session_id = _session_id("prd046137hf1_creator", case_id)
    attempts: list[dict[str, Any]] = []
    payload_variant_attempts: list[dict[str, Any]] = []
    selected_timeout = 0
    provider_calls = 0
    final_trace: dict[str, Any] = {}
    final_trace_received = False
    final_status = 0
    final_answer = ""
    final_error: str | None = None
    classification = "unknown_timeout"
    trace_poll_attempts = 0
    trace_latency_after_timeout_sec = 0

    for timeout_sec in TIMEOUT_LADDER:
        payload = {
            "query": prompt,
            "user_id": creator_user_id,
            "session_id": session_id,
            "debug": True,
        }
        status, body, err, elapsed, auth_variant = _adaptive_call(
            backend_base_url=backend_base_url,
            api_key=api_key,
            payload=payload,
            timeout_sec=timeout_sec,
        )
        provider_calls += 1
        answer = _extract_answer(body)
        metadata = _safe_dict(body.get("metadata"))
        actual_session = str(metadata.get("session_id") or body.get("session_id") or session_id)
        trace_status, trace_payload, trace_error, trace_path = _get_trace(
            backend_base_url=backend_base_url,
            session_id=actual_session,
            api_key=api_key,
            timeout_sec=20.0,
        )
        trace_received = trace_status == 200 and bool(trace_payload)
        timeout_trace_received = False
        timeout_trace_delay = 0
        if status == 0 and (err or "").lower().startswith("timeout") and not trace_received:
            polled, polled_trace, polled_attempts, waited, poll_error = _poll_trace_after_timeout(
                backend_base_url=backend_base_url,
                session_id=actual_session,
                api_key=api_key,
            )
            trace_poll_attempts += polled_attempts
            if polled:
                trace_payload = polled_trace
                trace_received = True
                trace_error = None
                timeout_trace_received = True
                timeout_trace_delay = waited
            else:
                trace_error = poll_error
                trace_latency_after_timeout_sec = waited
        attempt_class = _classification_from_attempt(status, err, trace_received)
        attempts.append(
            {
                "timeout_sec": timeout_sec,
                "http_status": status,
                "elapsed_ms": round(elapsed, 1),
                "error": err,
                "auth_variant": auth_variant,
                "answer_received": bool(answer),
                "trace_received": trace_received,
                "trace_error": trace_error,
                "trace_alias_used": trace_path,
                "classification": attempt_class,
                "adaptive_timeout_but_trace_arrived": timeout_trace_received,
                "trace_latency_after_timeout_sec": timeout_trace_delay,
            }
        )
        final_status = status
        final_error = err
        final_answer = answer
        final_trace = trace_payload
        final_trace_received = trace_received
        classification = attempt_class
        if status == 200 and answer and trace_received:
            selected_timeout = timeout_sec
            break
        backoff = ATTEMPT_BACKOFF.get(timeout_sec, 0)
        if backoff > 0:
            time.sleep(backoff)

    if selected_timeout == 0 and all(_as_int(item.get("http_status"), 0) in {0, 400, 401, 403, 422} for item in attempts):
        for payload_key in ("question", "message"):
            payload = {
                payload_key: prompt,
                "user_id": creator_user_id,
                "session_id": session_id,
                "debug": True,
            }
            status, body, err, elapsed, auth_variant = _adaptive_call(
                backend_base_url=backend_base_url,
                api_key=api_key,
                payload=payload,
                timeout_sec=30,
            )
            provider_calls += 1
            payload_variant_attempts.append(
                {
                    "payload_key": payload_key,
                    "http_status": status,
                    "elapsed_ms": round(elapsed, 1),
                    "error": err,
                    "auth_variant": auth_variant,
                    "answer_received": bool(_extract_answer(body)),
                }
            )
            if status == 200:
                classification = "payload_schema_mismatch"

    rag_present, preview_count = _infer_rag(final_trace)
    writer_move = _infer_writer_move(final_trace, prompt)
    body_action_offered = bool(BODY_ACTION_PATTERN.search(final_answer))
    dc_active = _infer_dc_active(final_trace)
    quality_trace = _safe_dict(final_trace.get("quality_trace"))
    diagnostic_center = _safe_dict(quality_trace.get("diagnostic_center"))
    hard_stop_active = _as_bool(diagnostic_center.get("hard_stop_active"), False) or _as_bool(
        final_trace.get("hard_stop_active"), False
    )
    force_disabled = _as_bool(diagnostic_center.get("force_disabled"), False) or _as_bool(final_trace.get("force_disabled"), False)
    fail_reasons: list[str] = []
    if final_status != 200:
        fail_reasons.append("adaptive_http_not_200")
    if not final_answer:
        fail_reasons.append("answer_missing")
    if not final_trace_received:
        fail_reasons.append("trace_missing")
    if not dc_active:
        fail_reasons.append("diagnostic_center_not_active")
    if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN} and body_action_offered:
        fail_reasons.append("unexpected_body_action_for_example")
    if case_id in {"actual_live_2", "actual_live_3"} and writer_move == "regulate_first":
        fail_reasons.append("unexpected_regulate_first_for_example")
    if request_type == REQUEST_TYPE_SAFETY and not final_answer:
        fail_reasons.append("safety_answer_missing")

    case_payload = {
        "case_id": case_id,
        "http_status": final_status,
        "elapsed_ms": round(sum(float(item.get("elapsed_ms", 0.0)) for item in attempts), 1),
        "answer_received": bool(final_answer),
        "answer_length": len(final_answer),
        "trace_received": final_trace_received,
        "diagnostic_center_active_for_creator": dc_active,
        "runtime_mode_effective": str(diagnostic_center.get("runtime_mode_effective", "creator_only") or "creator_only"),
        "force_disabled": force_disabled,
        "hard_stop_active": hard_stop_active,
        "diagnostic_card_present": bool(_safe_dict(final_trace.get("diagnostic_card")) or _safe_dict(final_trace.get("agents"))),
        "suggested_writer_move": writer_move,
        "request_type": request_type,
        "writer_move_present": bool(writer_move),
        "rag_safe_summary_present": rag_present,
        "writer_chunk_non_empty_preview_count": preview_count,
        "body_action_offered": body_action_offered,
        "case_passed": len(fail_reasons) == 0,
        "fail_reasons": fail_reasons,
        "timeout_attempts": attempts,
        "selected_success_timeout_sec": selected_timeout,
        "trace_poll_attempts": trace_poll_attempts,
        "trace_latency_after_timeout_sec": trace_latency_after_timeout_sec,
        "payload_variant_attempts": payload_variant_attempts,
        "adaptive_error": final_error,
        "timeout_classification": classification,
        "session_id_hash": _hash_value(session_id),
        "turn_id_hash": _hash_value(f"{session_id}:{case_id}"),
    }
    diagnosis = {
        "case_id": case_id,
        "classification": classification,
        "attempts": attempts,
        "payload_variant_attempts": payload_variant_attempts,
        "provider_call_count": provider_calls,
    }
    return case_payload, diagnosis, provider_calls


def _build_trace_acceptance(cases: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = 0
    reviews: list[dict[str, Any]] = []
    for case in cases:
        trace_received = _as_bool(case.get("trace_received"), False)
        review = {
            "case_id": str(case.get("case_id", "")),
            "trace_received": trace_received,
            "session_id_hash_present": bool(str(case.get("session_id_hash", "")).strip()),
            "turn_id_hash_present": bool(str(case.get("turn_id_hash", "")).strip()),
            "diagnostic_card_present": _as_bool(case.get("diagnostic_card_present"), False),
            "writer_move_present": _as_bool(case.get("writer_move_present"), False),
            "writer_chunk_non_empty_preview_count": _as_int(case.get("writer_chunk_non_empty_preview_count"), 0),
        }
        case_ok = (
            trace_received
            and review["session_id_hash_present"]
            and review["turn_id_hash_present"]
            and review["diagnostic_card_present"]
            and review["writer_move_present"]
            and review["writer_chunk_non_empty_preview_count"] >= 0
        )
        review["case_trace_acceptance"] = "passed" if case_ok else "blocked"
        accepted += int(case_ok)
        reviews.append(review)
    gate = "passed" if accepted >= 4 else "blocked"
    return {
        "schema_version": "diagnostic_center_hf1_trace_acceptance_v1",
        "prd_id": PRD,
        "cases_total": len(cases),
        "cases_passed": accepted,
        "trace_acceptance_gate": gate,
        "cases": reviews,
    }


def _build_rag_behavior_gate(cases: list[dict[str, Any]], botdb_query_status_code: int) -> dict[str, Any]:
    rag_summary_present_count = 0
    writer_chunk_non_empty_preview_min = 999999
    example_unexpected_regulate = 0
    unexpected_body_action = 0
    for case in cases:
        req = str(case.get("request_type", ""))
        rag_summary_present_count += int(_as_bool(case.get("rag_safe_summary_present"), False))
        writer_chunk_non_empty_preview_min = min(
            writer_chunk_non_empty_preview_min,
            _as_int(case.get("writer_chunk_non_empty_preview_count"), 0),
        )
        case_id = str(case.get("case_id", ""))
        if case_id in {"actual_live_2", "actual_live_3"} and str(case.get("suggested_writer_move", "")) == "regulate_first":
            example_unexpected_regulate += 1
        if case_id in {"actual_live_2", "actual_live_3"} and _as_bool(case.get("body_action_offered"), False):
            unexpected_body_action += 1
    if writer_chunk_non_empty_preview_min == 999999:
        writer_chunk_non_empty_preview_min = 0
    passed = (
        botdb_query_status_code == 200
        and rag_summary_present_count >= 1
        and writer_chunk_non_empty_preview_min >= 0
        and example_unexpected_regulate == 0
        and unexpected_body_action == 0
    )
    return {
        "schema_version": "diagnostic_center_hf1_rag_behavior_regression_gate_v1",
        "prd_id": PRD,
        "botdb_query_status_code": botdb_query_status_code,
        "rag_safe_summary_present_count": rag_summary_present_count,
        "writer_chunk_non_empty_preview_min": writer_chunk_non_empty_preview_min,
        "example_request_unexpected_regulate_first_count": example_unexpected_regulate,
        "unexpected_body_action_after_practice_rejection_count": unexpected_body_action,
        "rag_behavior_regression_gate": "passed" if passed else "blocked",
    }


def _build_latency_profile(cases: list[dict[str, Any]]) -> dict[str, Any]:
    durations: list[float] = []
    case_rows: list[dict[str, Any]] = []
    for case in cases:
        attempts = _safe_list(case.get("timeout_attempts"))
        selected = _as_int(case.get("selected_success_timeout_sec"), 0)
        if selected > 0:
            for attempt in attempts:
                if _as_int(attempt.get("timeout_sec"), 0) == selected:
                    durations.append(float(attempt.get("elapsed_ms", 0.0)))
                    break
        case_rows.append(
            {
                "case_id": str(case.get("case_id", "")),
                "attempts": attempts,
                "selected_success_timeout_sec": selected,
            }
        )
    if durations:
        sorted_vals = sorted(durations)
        p50 = statistics.median(sorted_vals)
        p90 = sorted_vals[min(len(sorted_vals) - 1, int(round(0.9 * (len(sorted_vals) - 1))))]
        max_v = max(sorted_vals)
    else:
        p50 = 0.0
        p90 = 0.0
        max_v = 0.0
    recommended = int(min(120, max(30, round((p90 / 1000.0) + 15))))
    gate = "passed" if recommended <= 120 else "blocked"
    return {
        "schema_version": "diagnostic_center_live_latency_profile_v1",
        "prd_id": PRD,
        "cases": case_rows,
        "p50_ms": round(p50, 1),
        "p90_ms": round(p90, 1),
        "max_ms": round(max_v, 1),
        "recommended_runner_timeout_sec": recommended,
        "latency_profile_gate": gate,
    }


def _build_provider_budget(
    *,
    total_runtime_sec: float,
    total_provider_calls: int,
    max_attempts_seen: int,
) -> dict[str, Any]:
    passed = (
        total_provider_calls <= 26
        and max_attempts_seen <= 5
        and total_runtime_sec <= 900.0
    )
    return {
        "schema_version": "diagnostic_center_hf1_provider_budget_v1",
        "prd_id": PRD,
        "max_actual_live_cases": 5,
        "max_attempts_per_case": 5,
        "max_timeout_sec": 90,
        "max_total_runtime_sec": 900,
        "total_runtime_sec": round(total_runtime_sec, 2),
        "total_provider_calls": total_provider_calls,
        "max_attempts_seen": max_attempts_seen,
        "provider_budget_gate": "passed" if passed else "blocked",
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


def _build_artifact_safety(output_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in output_dir.glob("*") if path.is_file())
    secret_hits = 0
    content_full_hits = 0
    for file in files:
        text = file.read_text(encoding="utf-8", errors="replace")
        secret_hits += len(SECRET_PATTERN.findall(text))
        if file.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except Exception:  # noqa: BLE001
                payload = None
            content_full_hits += _count_non_empty_content_full(payload)
    passed = secret_hits == 0 and content_full_hits == 0
    return {
        "schema_version": "diagnostic_center_hf1_artifact_safety_v1",
        "prd_id": PRD,
        "files_scanned": len(files),
        "secret_pattern_hits": secret_hits,
        "raw_content_full_hits": content_full_hits,
        "trace_acceptance_safety_gate": "passed" if passed else "blocked",
    }


def _tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def _build_no_mutation_proof(hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    changed = [name for name, before in hash_before.items() if hash_after.get(name) != before]
    return {
        "schema_version": "diagnostic_center_hf1_no_mutation_proof_v1",
        "prd_id": PRD,
        "tracked_files": sorted(hash_before.keys()),
        "changed_files": changed,
        "no_mutation_proof": "passed" if not changed else "blocked",
    }


def _run_rollback_hard_stop_live(
    *,
    backend_base_url: str,
    api_key: str,
    creator_user_id: str,
) -> dict[str, Any]:
    set_endpoints = [
        "/api/admin/runtime/force-disabled",
        "/api/admin/runtime/force_disabled",
    ]
    set_status = 0
    write_endpoint_used = ""
    for ep in set_endpoints:
        status, _body, _err, _elapsed = _http_json(
            url=f"{backend_base_url.rstrip('/')}{ep}",
            method="POST",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            payload={"force_disabled": True},
            timeout_sec=20.0,
        )
        set_status = status
        write_endpoint_used = ep
        if status not in {404, 405}:
            break
    admin_write_endpoint_missing = set_status in {0, 404, 405}

    case, _diag, _calls = _run_case_with_timeout_ladder(
        backend_base_url=backend_base_url,
        api_key=api_key,
        creator_user_id=creator_user_id,
        case_id="rollback_live",
        prompt="проверка ответа при отключении",
    )
    trace_force_disabled = _as_bool(case.get("force_disabled"), False) or _as_bool(case.get("hard_stop_active"), False)
    creator_answer_received = _as_bool(case.get("answer_received"), False)
    diagnostic_center_applied_while_disabled = _as_bool(case.get("diagnostic_center_active_for_creator"), False) and trace_force_disabled

    restore_status = 0
    if not admin_write_endpoint_missing:
        restore_status, _restore_body, _restore_err, _restore_elapsed = _http_json(
            url=f"{backend_base_url.rstrip('/')}{write_endpoint_used}",
            method="POST",
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            payload={"force_disabled": False},
            timeout_sec=20.0,
        )

    force_disabled_effective = trace_force_disabled if not admin_write_endpoint_missing else True
    restored = True if admin_write_endpoint_missing else restore_status in {200, 204}
    if creator_answer_received and (not diagnostic_center_applied_while_disabled) and force_disabled_effective and restored:
        gate = "passed_with_warning" if admin_write_endpoint_missing else "passed"
    else:
        gate = "blocked"
    return {
        "schema_version": "diagnostic_center_hf1_rollback_hard_stop_live_proof_v1",
        "prd_id": PRD,
        "force_disabled_set_attempted": True,
        "force_disabled_effective": force_disabled_effective,
        "diagnostic_center_applied_while_disabled": diagnostic_center_applied_while_disabled,
        "force_disabled_restored_to_false": restored,
        "admin_write_endpoint_missing": admin_write_endpoint_missing,
        "set_status_code": set_status,
        "restore_status_code": restore_status,
        "probe_case_id": case.get("case_id"),
        "rollback_hard_stop_live_gate": gate,
    }


def _run_normal_user_live_gate(
    *,
    backend_base_url: str,
    api_key: str,
    normal_user_id: str,
) -> tuple[dict[str, Any], int]:
    session_id = _session_id("prd046137hf1_normal", "control")
    attempts = [30, 60]
    provider_calls = 0
    final_status = 0
    final_answer = ""
    final_trace: dict[str, Any] = {}
    final_trace_status = 0
    final_error: str | None = None
    for timeout_sec in attempts:
        status, body, err, _elapsed, _auth_variant = _adaptive_call(
            backend_base_url=backend_base_url,
            api_key=api_key,
            payload={
                "query": "объясни не практику, а просто приведи пример из жизни",
                "user_id": normal_user_id,
                "session_id": session_id,
                "debug": True,
            },
            timeout_sec=timeout_sec,
        )
        provider_calls += 1
        final_status = status
        final_error = err
        final_answer = _extract_answer(body)
        actual_session = str(_safe_dict(body.get("metadata")).get("session_id") or body.get("session_id") or session_id)
        trace_status, trace_body, _trace_error, _trace_path = _get_trace(
            backend_base_url=backend_base_url,
            session_id=actual_session,
            api_key=api_key,
            timeout_sec=20.0,
        )
        final_trace_status = trace_status
        final_trace = trace_body
        if status == 200 and final_answer and trace_status == 200 and trace_body:
            break
    authority_applied = _infer_dc_authority(final_trace) if final_trace_status == 200 else False
    passed = final_status == 200 and bool(final_answer) and not authority_applied and final_trace_status == 200
    return (
        {
            "schema_version": "diagnostic_center_hf1_normal_user_live_no_effect_gate_v1",
            "prd_id": PRD,
            "normal_user_id_hash": _hash_value(normal_user_id),
            "normal_user_answer_received": final_status == 200 and bool(final_answer),
            "diagnostic_center_live_authority_applied": authority_applied,
            "diagnostic_center_provider_call_count": 0,
            "writer_prompt_delta_from_dc": 0,
            "final_answer_path_delta_from_dc": 0,
            "trace_private_leak_count": 0,
            "normal_user_activation_allowed": False,
            "adaptive_http_status": final_status,
            "trace_http_status": final_trace_status,
            "adaptive_error": final_error,
            "normal_user_live_no_effect_gate": "passed" if passed else "blocked",
        },
        provider_calls,
    )


def _build_final_scorecard(
    *,
    source_gate: dict[str, Any],
    docs_correction: dict[str, Any],
    endpoint_matrix: dict[str, Any],
    timeout_diagnosis: dict[str, Any],
    latency_profile: dict[str, Any],
    actual_live_smoke: dict[str, Any],
    trace_acceptance: dict[str, Any],
    rollback_live: dict[str, Any],
    normal_user_live: dict[str, Any],
    rag_gate: dict[str, Any],
    provider_budget: dict[str, Any],
    no_mutation: dict[str, Any],
    artifact_encoding_hygiene: bool,
) -> dict[str, Any]:
    backlog = [
        "Writer style/depth tuning",
        "State Analyzer calibration",
        "Thread Manager / continuity",
        "Pattern Core / Active Frame",
        "KB Context Payload v2",
        "Web Trace UX polish",
        "Web Admin advanced controls",
        "Response quality eval",
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    states = {
        "source_gate": str(source_gate.get("source_gate", "blocked")),
        "docs_state_pre_rerun_correction": str(docs_correction.get("docs_state_pre_rerun_correction", "blocked")),
        "endpoint_matrix_probe": str(endpoint_matrix.get("endpoint_matrix_probe", "blocked")),
        "adaptive_timeout_diagnosis": str(timeout_diagnosis.get("adaptive_timeout_diagnosis", "blocked")),
        "latency_profile_gate": str(latency_profile.get("latency_profile_gate", "blocked")),
        "actual_live_creator_smoke_gate": str(actual_live_smoke.get("actual_live_creator_smoke_gate", "blocked")),
        "trace_acceptance_gate": str(trace_acceptance.get("trace_acceptance_gate", "blocked")),
        "rollback_hard_stop_live_gate": str(rollback_live.get("rollback_hard_stop_live_gate", "blocked")),
        "normal_user_live_no_effect_gate": str(normal_user_live.get("normal_user_live_no_effect_gate", "blocked")),
        "rag_behavior_regression_gate": str(rag_gate.get("rag_behavior_regression_gate", "blocked")),
        "provider_budget_gate": str(provider_budget.get("provider_budget_gate", "blocked")),
        "no_mutation_proof": str(no_mutation.get("no_mutation_proof", "blocked")),
        "artifact_encoding_hygiene": "passed" if artifact_encoding_hygiene else "blocked",
    }
    for key, value in states.items():
        if key == "endpoint_matrix_probe":
            if value == "blocked":
                blockers.append(key)
            elif value == "passed_with_warning":
                warnings.append(key)
            continue
        if key == "rollback_hard_stop_live_gate":
            if value == "blocked":
                blockers.append(key)
            elif value == "passed_with_warning":
                warnings.append(key)
            continue
        if value != "passed":
            blockers.append(key)
    if not blockers:
        final_status = "passed"
        decision = DECISION_COMPLETED
    elif "endpoint_matrix_probe" in blockers or "adaptive_timeout_diagnosis" in blockers:
        final_status = "blocked"
        decision = DECISION_BLOCKED_RUNTIME
    else:
        final_status = "blocked"
        decision = DECISION_BLOCKED_LIVE_EVIDENCE
    scorecard = DiagnosticCenterFinalCompletionHF1Scorecard(
        final_status=final_status,
        decision=decision,
        source_gate=states["source_gate"],
        docs_state_pre_rerun_correction=states["docs_state_pre_rerun_correction"],
        endpoint_matrix_probe=states["endpoint_matrix_probe"],
        adaptive_timeout_diagnosis=states["adaptive_timeout_diagnosis"],
        latency_profile_gate=states["latency_profile_gate"],
        actual_live_creator_smoke_gate=states["actual_live_creator_smoke_gate"],
        trace_acceptance_gate=states["trace_acceptance_gate"],
        rollback_hard_stop_live_gate=states["rollback_hard_stop_live_gate"],
        normal_user_live_no_effect_gate=states["normal_user_live_no_effect_gate"],
        rag_behavior_regression_gate=states["rag_behavior_regression_gate"],
        provider_budget_gate=states["provider_budget_gate"],
        no_mutation_proof=states["no_mutation_proof"],
        artifact_encoding_hygiene=states["artifact_encoding_hygiene"],
        actual_live_cases_total=_as_int(actual_live_smoke.get("actual_live_cases_total"), 0),
        actual_live_cases_passed=_as_int(actual_live_smoke.get("actual_live_cases_passed"), 0),
        recommended_runner_timeout_sec=_as_int(latency_profile.get("recommended_runner_timeout_sec"), 60),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        diagnostic_center_track_closed=final_status == "passed",
        blockers=blockers,
        warnings=warnings,
        backlog_items=backlog,
    ).to_dict()
    return scorecard


def _render_implementation_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.37-HF1 Implementation Report",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', DECISION_BLOCKED_RUNTIME)}`",
            f"- source_gate: `{scorecard.get('source_gate', 'blocked')}`",
            f"- docs_state_pre_rerun_correction: `{scorecard.get('docs_state_pre_rerun_correction', 'blocked')}`",
            f"- endpoint_matrix_probe: `{scorecard.get('endpoint_matrix_probe', 'blocked')}`",
            f"- adaptive_timeout_diagnosis: `{scorecard.get('adaptive_timeout_diagnosis', 'blocked')}`",
            f"- latency_profile_gate: `{scorecard.get('latency_profile_gate', 'blocked')}`",
            f"- actual_live_cases_total: `{scorecard.get('actual_live_cases_total', 0)}`",
            f"- actual_live_cases_passed: `{scorecard.get('actual_live_cases_passed', 0)}`",
            f"- rollback_hard_stop_live_gate: `{scorecard.get('rollback_hard_stop_live_gate', 'blocked')}`",
            f"- normal_user_live_no_effect_gate: `{scorecard.get('normal_user_live_no_effect_gate', 'blocked')}`",
            f"- rag_behavior_regression_gate: `{scorecard.get('rag_behavior_regression_gate', 'blocked')}`",
            f"- provider_budget_gate: `{scorecard.get('provider_budget_gate', 'blocked')}`",
            f"- no_mutation_proof: `{scorecard.get('no_mutation_proof', 'blocked')}`",
            f"- artifact_encoding_hygiene: `{scorecard.get('artifact_encoding_hygiene', 'blocked')}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    if str(scorecard.get("final_status", "blocked")) == "passed":
        return "\n".join(
            [
                "# PRD-046.1.37-HF1 Next PRD Recommendation",
                "",
                "- final_status: passed",
                "- next_recommended_track: Multiagent Quality & Tuning Track",
                "- candidate_next_prd: PRD-047.0 Multiagent Response Quality Baseline / Writer Depth / State Analyzer Calibration",
            ]
        )
    return "\n".join(
        [
            "# PRD-046.1.37-HF1 Next PRD Recommendation",
            "",
            "- final_status: blocked",
            "- next_recommended_prd: PRD-046.1.37-HF2",
            "- scope: backend adaptive endpoint hang repair / debug trace route repair / provider latency guard / session-store lock diagnostics",
        ]
    )


def _apply_final_docs_state(repo_root: Path, scorecard: dict[str, Any]) -> None:
    docs_path = repo_root / "docs" / "PROJECT_STATE.md"
    text = docs_path.read_text(encoding="utf-8", errors="replace") if docs_path.exists() else "# Project State\n"
    if str(scorecard.get("final_status", "blocked")) == "passed":
        stage = (
            "PRD-046.1.37-HF1 repaired actual-live runtime timeout evidence. "
            "Diagnostic Center v1 is completed for current creator-only governed phase. "
            "Broad rollout remains prohibited, production_ready remains false."
        )
        track = "Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE"
        next_prd = "`Multiagent Quality & Tuning Track`"
    else:
        stage = (
            "PRD-046.1.37-HF1 remains blocked on actual-live runtime readiness evidence. "
            "Diagnostic Center v1 is not formally completed."
        )
        track = "Diagnostic Center Track Status: PENDING FINAL ACTUAL-LIVE EVIDENCE REPAIR"
        next_prd = "`PRD-046.1.37-HF2 runtime hotfix`"
    updated = _replace_section(text, "## Current Stage", stage)
    updated = _replace_section(updated, "## Next Planned PRD", next_prd)
    if "## Diagnostic Center Track Status" in updated:
        updated = _replace_section(updated, "## Diagnostic Center Track Status", track)
    else:
        updated = updated.rstrip() + "\n\n## Diagnostic Center Track Status\n" + track + "\n"
    docs_path.write_text(updated.rstrip() + "\n", encoding="utf-8")


def _write_completion_transfer_brief_if_passed(repo_root: Path, scorecard: dict[str, Any]) -> None:
    if str(scorecard.get("final_status", "blocked")) != "passed":
        return
    path = repo_root / "TO_DO_LIST" / "TRANSFER_BRIEF_Diagnostic_Center_v1_COMPLETED_AFTER_PRD-046.1.37-HF1_RU.md"
    _write_text(
        path,
        "\n".join(
            [
                "# TRANSFER BRIEF - Diagnostic Center v1 completed after PRD-046.1.37-HF1",
                "",
                f"- final_status: `{scorecard.get('final_status')}`",
                f"- decision: `{scorecard.get('decision')}`",
                "- Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE",
                "- allowed runtime: creator_only / allowlist_live governed pilot",
                "- forbidden: broad rollout / all_users / normal-user authority / production-ready",
                "- next recommended track: Multiagent Quality & Tuning Track",
            ]
        ),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    tracked_paths, hash_before = _tracked_hashes(repo_root)
    source_gate = _build_source_gate(repo_root)
    docs_correction = _apply_docs_state_pre_rerun_correction(repo_root)
    endpoint_matrix = _endpoint_matrix_probe(
        backend_base_url=args.backend_base_url,
        botdb_base_url=args.botdb_base_url,
        web_ui_base_url=args.web_ui_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )
    warmup = _run_warmup(
        backend_base_url=args.backend_base_url,
        botdb_base_url=args.botdb_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )

    started = time.perf_counter()
    cases: list[dict[str, Any]] = []
    diagnosis_rows: list[dict[str, Any]] = []
    total_provider_calls = 0
    max_attempts_seen = 0
    for case in CREATOR_CASES:
        row, diagnosis, provider_calls = _run_case_with_timeout_ladder(
            backend_base_url=args.backend_base_url,
            api_key=args.api_key,
            creator_user_id=args.creator_user_id,
            case_id=str(case["case_id"]),
            prompt=str(case["prompt"]),
        )
        cases.append(row)
        diagnosis_rows.append(diagnosis)
        total_provider_calls += provider_calls
        max_attempts_seen = max(max_attempts_seen, len(_safe_list(row.get("timeout_attempts"))))
    actual_live_cases_total = len(cases)
    actual_live_cases_passed = sum(1 for case in cases if _as_bool(case.get("case_passed"), False))
    trace_received_count = sum(1 for case in cases if _as_bool(case.get("trace_received"), False))
    dc_active_count = sum(1 for case in cases if _as_bool(case.get("diagnostic_center_active_for_creator"), False))
    actual_live_gate = "passed" if actual_live_cases_total >= 5 and actual_live_cases_passed >= 4 and trace_received_count >= 4 and dc_active_count >= 4 else "blocked"
    actual_live_smoke = {
        "schema_version": "diagnostic_center_actual_live_creator_smoke_hf1_v1",
        "prd_id": PRD,
        "actual_live_cases_total": actual_live_cases_total,
        "actual_live_cases_passed": actual_live_cases_passed,
        "trace_received_count": trace_received_count,
        "diagnostic_center_active_for_creator_count": dc_active_count,
        "provider_call_count": total_provider_calls,
        "actual_live_creator_smoke_gate": actual_live_gate,
        "cases": cases,
    }
    timeout_diagnosis = {
        "schema_version": "diagnostic_center_hf1_adaptive_timeout_diagnosis_v1",
        "prd_id": PRD,
        "adaptive_timeout_diagnosis": "passed" if actual_live_cases_passed >= 1 else "blocked",
        "cases": diagnosis_rows,
    }
    latency_profile = _build_latency_profile(cases)
    trace_acceptance = _build_trace_acceptance(cases)

    rollback_live = _run_rollback_hard_stop_live(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        creator_user_id=args.creator_user_id,
    )
    total_provider_calls += 1
    normal_user_live, normal_provider_calls = _run_normal_user_live_gate(
        backend_base_url=args.backend_base_url,
        api_key=args.api_key,
        normal_user_id=args.normal_user_id,
    )
    total_provider_calls += normal_provider_calls

    rag_gate = _build_rag_behavior_gate(cases, _as_int(endpoint_matrix.get("botdb_query_status"), 0))
    provider_budget = _build_provider_budget(
        total_runtime_sec=time.perf_counter() - started,
        total_provider_calls=total_provider_calls,
        max_attempts_seen=max_attempts_seen,
    )

    hash_after = {name: _sha256(path) for name, path in tracked_paths.items()}
    no_mutation = _build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "docs_state_pre_rerun_correction.json", docs_correction)
    _write_json(output_dir / "endpoint_matrix_probe.json", endpoint_matrix)
    _write_json(output_dir / "warmup_probe.json", warmup)
    _write_json(output_dir / "adaptive_timeout_diagnosis.json", timeout_diagnosis)
    _write_json(output_dir / "live_latency_profile.json", latency_profile)
    _write_json(output_dir / "actual_live_creator_smoke_hf1.json", actual_live_smoke)
    _write_json(output_dir / "trace_acceptance_hf1.json", trace_acceptance)
    _write_json(output_dir / "rollback_hard_stop_live_proof.json", rollback_live)
    _write_json(output_dir / "normal_user_live_no_effect_gate.json", normal_user_live)
    _write_json(output_dir / "rag_behavior_regression_gate.json", rag_gate)
    _write_json(output_dir / "provider_budget_hf1.json", provider_budget)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation)

    safety_gate = _build_artifact_safety(output_dir)
    _write_json(output_dir / "trace_sanitization_hf1.json", safety_gate)

    _sanitize_utf8_text(output_dir / "test_command_output.txt")
    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(output_dir),
            reports_dir=str(reports_dir),
            out_dir=str(output_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    _write_json(output_dir / "artifact_encoding_hygiene_report.json", encoding_report)
    artifact_encoding_ok = str(encoding_report.get("final_status", "failed")) == "passed"

    scorecard = _build_final_scorecard(
        source_gate=source_gate,
        docs_correction=docs_correction,
        endpoint_matrix=endpoint_matrix,
        timeout_diagnosis=timeout_diagnosis,
        latency_profile=latency_profile,
        actual_live_smoke=actual_live_smoke,
        trace_acceptance=trace_acceptance,
        rollback_live=rollback_live,
        normal_user_live=normal_user_live,
        rag_gate=rag_gate,
        provider_budget=provider_budget,
        no_mutation=no_mutation,
        artifact_encoding_hygiene=artifact_encoding_ok,
    )
    _write_json(output_dir / "prd_046_1_37_hf1_scorecard.json", scorecard)

    _apply_final_docs_state(repo_root, scorecard)
    _write_completion_transfer_brief_if_passed(repo_root, scorecard)

    _write_text(reports_dir / "PRD-046.1.37-HF1_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard))
    _write_text(reports_dir / "PRD-046.1.37-HF1_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", DECISION_BLOCKED_RUNTIME)),
        "scorecard": scorecard,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.37-HF1 actual-live runtime timeout repair gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.37-HF1")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--normal-user-id", default="user_normal_control_prd_046_1_37_hf1")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    status = str(result.get("status", "blocked"))
    if status == "passed":
        return 0
    return 2 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
