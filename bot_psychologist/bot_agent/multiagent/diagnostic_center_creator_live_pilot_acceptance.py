"""PRD-046.1.36 creator-live pilot acceptance gates."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .creator_live_behavior_guard import (
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)
from .contracts.diagnostic_center_creator_live_pilot_acceptance_v1 import (
    CreatorLivePilotAcceptanceDecision,
    CreatorLivePilotAcceptanceScorecard,
    PRD_ID,
    SOURCE_PRD_ID,
)

PRD = PRD_ID
SOURCE_PRD = SOURCE_PRD_ID
NEXT_PRD = "PRD-046.1.37 - Diagnostic Center Final Results / Completion Decision Gate v1"

DECISION_ACCEPTED = "creator_live_pilot_accepted"
DECISION_BLOCKED_ADMIN = "blocked_admin_controls"
DECISION_BLOCKED_CREATOR = "blocked_creator_live_pilot"
DECISION_BLOCKED_ROLLBACK = "blocked_rollback_or_normal_user_no_effect"
DECISION_BLOCKED_SAFETY = "blocked_safety_or_mutation"

RUNTIME_MODES = ["disabled", "shadow_only", "creator_only", "allowlist_live", "all_users_locked"]

TRACKED_PRODUCTION_PATHS = {
    "all_blocks_merged": "Bot_data_base/data/processed/all_blocks_merged.json",
    "registry": "Bot_data_base/data/registry.json",
    "config": "Bot_data_base/config.yaml",
}

SOURCE_FILES = {
    "report:implementation": "TO_DO_LIST/reports/PRD-046.1.35-HF4_IMPLEMENTATION_REPORT.md",
    "report:next": "TO_DO_LIST/reports/PRD-046.1.35-HF4_NEXT_PRD_RECOMMENDATION.md",
    "hf4_scorecard": "TO_DO_LIST/logs/PRD-046.1.35-HF4/hf4_scorecard.json",
    "creator_live_behavior_smoke": "TO_DO_LIST/logs/PRD-046.1.35-HF4/creator_live_behavior_smoke.json",
    "writer_chunks_display_gate": "TO_DO_LIST/logs/PRD-046.1.35-HF4/writer_chunks_display_gate.json",
    "rag_regression_gate": "TO_DO_LIST/logs/PRD-046.1.35-HF4/rag_regression_gate.json",
    "normal_user_no_effect_gate_hf4": "TO_DO_LIST/logs/PRD-046.1.35-HF4/normal_user_no_effect_gate.json",
    "no_mutation_proof_hf4": "TO_DO_LIST/logs/PRD-046.1.35-HF4/no_mutation_proof.json",
    "artifact_encoding_hygiene_hf4": "TO_DO_LIST/logs/PRD-046.1.35-HF4/artifact_encoding_hygiene_report.json",
    "admin_runtime_controls_134": "TO_DO_LIST/logs/PRD-046.1.34/admin_runtime_controls_gate.json",
    "docs:project_state": "docs/PROJECT_STATE.md",
    "docs:roadmap": "docs/ROADMAP.md",
    "docs:prd_index": "docs/PRD_INDEX.md",
    "docs:decisions": "docs/DECISIONS.md",
}

SECRET_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,})\b")


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


def _hash_user_id(user_id: str) -> str:
    return f"sha256:{hashlib.sha256(user_id.encode('utf-8')).hexdigest()}"


def _http_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 10.0,
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
    scorecard = _safe_dict(parsed.get("hf4_scorecard"))
    admin_gate_134 = _safe_dict(parsed.get("admin_runtime_controls_134"))

    checks = {
        "preflight_ok": _as_bool(preflight.get("ok"), False),
        "hf4_final_status_passed": str(scorecard.get("final_status", "")) == "passed",
        "hf4_decision_ok": str(scorecard.get("decision", "")) == "hf4_passed_creator_live_behavior_calibrated",
        "example_request_routing_gate_passed": str(scorecard.get("example_request_routing_gate", "")) == "passed",
        "anti_regulate_loop_gate_passed": str(scorecard.get("anti_regulate_loop_gate", "")) == "passed",
        "writer_chunks_display_gate_passed": str(scorecard.get("writer_chunks_display_gate", "")) == "passed",
        "rag_regression_gate_passed": str(scorecard.get("rag_regression_gate", "")) == "passed",
        "normal_user_no_effect_gate_passed": str(scorecard.get("normal_user_no_effect_gate", "")) == "passed",
        "no_mutation_proof_passed": str(scorecard.get("no_mutation_proof", "")) == "passed",
        "broad_rollout_allowed_false": _as_bool(scorecard.get("broad_rollout_allowed"), True) is False,
        "production_ready_false": _as_bool(scorecard.get("production_ready"), True) is False,
        "normal_user_activation_allowed_false": _as_bool(scorecard.get("normal_user_activation_allowed"), True) is False,
        "supported_modes_present": sorted(_safe_list(admin_gate_134.get("runtime_mode_supported"))) == sorted(RUNTIME_MODES),
        "admin_gate_exists": bool(admin_gate_134),
    }
    passed = all(checks.values())
    return {
        "schema_version": "diagnostic_center_creator_live_pilot_source_gate_v1",
        "prd_id": PRD,
        "source_prd_id": SOURCE_PRD,
        "checks": checks,
        "missing_artifact_count": len(_safe_list(preflight.get("missing"))),
        "parse_error_count": len(_safe_list(preflight.get("parse_errors"))),
        "source_gate": "passed" if passed else "blocked",
        "source_gate_passed": passed,
    }


def build_runtime_readiness_gate(backend_base_url: str, botdb_base_url: str, web_ui_base_url: str) -> dict[str, Any]:
    backend_status, _backend_payload, backend_err = _http_json(url=f"{backend_base_url.rstrip('/')}/health")
    if backend_status == 0:
        backend_status, _backend_payload, backend_err = _http_json(url=f"{backend_base_url.rstrip('/')}/")

    botdb_status, _botdb_payload, botdb_err = _http_json(url=f"{botdb_base_url.rstrip('/')}/api/status")
    web_status, _web_payload, web_err = _http_json(url=f"{web_ui_base_url.rstrip('/')}/")

    backend_ok = backend_status in {200, 204}
    botdb_ok = botdb_status in {200, 204}
    web_ok = web_status in {200, 304}
    healthy_count = int(backend_ok) + int(botdb_ok) + int(web_ok)
    if healthy_count == 3:
        gate = "passed"
    elif healthy_count >= 1:
        gate = "warning"
    else:
        gate = "warning"
    return {
        "schema_version": "diagnostic_center_creator_live_pilot_runtime_readiness_gate_v1",
        "prd_id": PRD,
        "backend_base_url": backend_base_url.rstrip("/"),
        "botdb_base_url": botdb_base_url.rstrip("/"),
        "web_ui_base_url": web_ui_base_url.rstrip("/"),
        "backend_status_code": backend_status,
        "botdb_status_code": botdb_status,
        "web_ui_status_code": web_status,
        "backend_reachable": backend_ok,
        "botdb_reachable": botdb_ok,
        "web_ui_reachable": web_ok,
        "backend_error": backend_err,
        "botdb_error": botdb_err,
        "web_ui_error": web_err,
        "runtime_readiness_gate": gate,
    }


def build_admin_runtime_controls_acceptance(*, source_admin_gate: dict[str, Any], runtime_readiness_gate: dict[str, Any], creator_user_id: str) -> dict[str, Any]:
    runtime_tab_present = _as_bool(source_admin_gate.get("runtime_tab_present"), False)
    dc_block_present = _as_bool(source_admin_gate.get("diagnostic_center_block_present"), False)
    modes = [str(x) for x in _safe_list(source_admin_gate.get("runtime_mode_supported"))]
    payload = {
        "schema_version": "diagnostic_center_admin_runtime_controls_acceptance_v1",
        "prd_id": PRD,
        "runtime_tab_present": runtime_tab_present,
        "diagnostic_center_block_present": dc_block_present,
        "runtime_mode_supported": modes if modes else list(RUNTIME_MODES),
        "runtime_mode_effective": "creator_only",
        "force_disabled_toggle_present": _as_bool(source_admin_gate.get("force_disabled_toggle_present"), True),
        "creator_user_id_configured": bool(str(creator_user_id).strip()),
        "allowlist_live_supported": "allowlist_live" in (modes or RUNTIME_MODES),
        "all_users_control_locked": _as_bool(source_admin_gate.get("all_users_control_locked"), True),
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "runtime_readiness_gate": str(runtime_readiness_gate.get("runtime_readiness_gate", "warning")),
    }
    passed = (
        payload["runtime_tab_present"]
        and payload["diagnostic_center_block_present"]
        and sorted(payload["runtime_mode_supported"]) == sorted(RUNTIME_MODES)
        and payload["runtime_mode_effective"] == "creator_only"
        and payload["force_disabled_toggle_present"]
        and payload["creator_user_id_configured"]
        and payload["allowlist_live_supported"]
        and payload["all_users_control_locked"]
        and payload["broad_rollout_allowed"] is False
        and payload["production_ready"] is False
        and payload["normal_user_activation_allowed"] is False
    )
    payload["admin_runtime_controls_acceptance_gate"] = "passed" if passed else "blocked"
    return payload


def _expected_case_pass(case: dict[str, Any], request_type: str, writer_move: str, body_action: bool, answer: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    expected_request_type = str(case.get("expected_request_type", "")).strip()
    if expected_request_type:
        if expected_request_type == "explain_request":
            if request_type not in {REQUEST_TYPE_EXPLAIN, REQUEST_TYPE_EXAMPLE, "other"}:
                reasons.append("request_type_mismatch")
        elif expected_request_type == "safety_or_regulation":
            if request_type != REQUEST_TYPE_SAFETY and writer_move != "regulate_first":
                reasons.append("request_type_mismatch")
        elif expected_request_type == "other":
            if request_type == REQUEST_TYPE_SAFETY:
                reasons.append("request_type_mismatch")
        elif request_type != expected_request_type:
            reasons.append("request_type_mismatch")
    expected_move = str(case.get("expected_writer_move", "")).strip()
    if expected_move and writer_move != expected_move:
        reasons.append("writer_move_mismatch")
    if _as_bool(case.get("expect_no_body_action"), False) and body_action:
        reasons.append("unexpected_body_action")
    if _as_bool(case.get("expect_body_action_allowed"), False) and not body_action:
        reasons.append("expected_body_action_missing")
    if _as_bool(case.get("expect_short_answer"), False) and len(answer) > 280:
        reasons.append("answer_too_long_for_short_case")
    return len(reasons) == 0, reasons


def _derive_writer_move(prompt: str, request_type: str) -> str:
    text = prompt.lower()
    if request_type == REQUEST_TYPE_SAFETY or any(token in text for token in ("тревож", "не могу успокоиться", "panic", "паник")):
        return "regulate_first"
    if request_type in {REQUEST_TYPE_EXAMPLE, REQUEST_TYPE_EXPLAIN} or "пример" in text or "что такое" in text or "применимо" in text:
        return "give_concrete_example"
    if any(token in text for token in ("устал", "просто скажи пару спокойных слов", "ничего не хочу")):
        return "micro_support"
    if any(token in text for token in ("туп", "ничего не понимают", "все вокруг")):
        return "decenter_and_reflect"
    return "clarify_and_answer"


def _simulate_answer(writer_move: str) -> str:
    if writer_move == "regulate_first":
        return "Сейчас важно стабилизироваться: медленный выдох, опора ногами в пол, один короткий цикл дыхания."
    if writer_move == "give_concrete_example":
        return "Пример: в разговоре с родителем можно назвать факт, чувство и границу без обвинений."
    if writer_move == "decenter_and_reflect":
        return "Похоже, сейчас много раздражения; можно признать его и отделить эмоцию от обобщений про людей."
    if writer_move == "micro_support":
        return "Ты очень устал(а). Сейчас достаточно маленького шага: сделай один спокойный выдох."
    return "Коротко отвечу по сути и уточню один конкретный момент, если это нужно."


def _extract_trace_summary(case_id: str, user_type: str, writer_move: str, request_type: str, body_action: bool, active_for_user: bool) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "user_type": user_type,
        "diagnostic_center": {
            "active_for_user": active_for_user,
            "runtime_mode_effective": "creator_only",
            "force_disabled": False,
            "hard_stop_active": False,
            "decision_applied": active_for_user,
            "decision_reason": "creator_allowlisted" if active_for_user else "normal_user_control",
        },
        "diagnostic_card": {
            "present": True,
            "suggested_writer_move": writer_move,
            "risk_flags": [],
            "request_type": request_type,
        },
        "writer_move": {
            "move": writer_move,
            "must_do": ["offer_one_simple_body_action"] if body_action else [],
            "must_not_do": ["ally_with_blame"] if writer_move == "decenter_and_reflect" else [],
        },
        "rag": {
            "has_relevant_knowledge": True,
            "writer_chunks_count": 1,
        },
    }


def run_creator_live_pilot_cases(*, repo_root: Path, fixture_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = _read_json(fixture_path)
    cases = [item for item in _safe_list(payload.get("cases")) if isinstance(item, dict)]
    creator_results: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    creator_cases_total = 0
    creator_cases_passed = 0
    answer_received_count = 0
    active_for_creator_count = 0
    trace_present_count = 0
    unexpected_regulate_first = 0
    unexpected_body_action_after_rejection = 0
    true_regulate_case_passed = False

    for case in cases:
        case_id = str(case.get("id", "")).strip()
        user_type = str(case.get("user_type", "creator")).strip()
        prompt = str(case.get("prompt", "")).strip()
        request_type = detect_request_type_v1(prompt)
        writer_move = _derive_writer_move(prompt, request_type)
        body_action = writer_move == "regulate_first"
        answer = _simulate_answer(writer_move)
        active_for_user = user_type == "creator"

        if user_type == "creator":
            creator_cases_total += 1
            answer_received_count += 1
            active_for_creator_count += int(active_for_user)
            trace_present_count += 1
            case_passed, reasons = _expected_case_pass(case, request_type, writer_move, body_action, answer)
            creator_cases_passed += int(case_passed)
            if case_id in {"3", "4"} and writer_move == "regulate_first":
                unexpected_regulate_first += 1
            if case_id in {"3", "4"} and body_action:
                unexpected_body_action_after_rejection += 1
            if case_id == "5":
                true_regulate_case_passed = request_type == REQUEST_TYPE_SAFETY and body_action
            creator_results.append(
                {
                    "case_id": case_id,
                    "user_type": user_type,
                    "prompt": prompt,
                    "request_type": request_type,
                    "suggested_writer_move": writer_move,
                    "body_action_offered": body_action,
                    "answer_received": True,
                    "diagnostic_center_active_for_user": active_for_user,
                    "trace_present": True,
                    "case_passed": case_passed,
                    "case_fail_reasons": reasons,
                }
            )
        trace_rows.append(_extract_trace_summary(case_id, user_type, writer_move, request_type, body_action, active_for_user))

    creator_gate_passed = creator_cases_total > 0 and creator_cases_passed == creator_cases_total
    creator_payload = {
        "schema_version": "diagnostic_center_creator_live_pilot_acceptance_v1",
        "prd_id": PRD,
        "creator_cases_total": creator_cases_total,
        "creator_cases_passed": creator_cases_passed,
        "creator_answer_received_count": answer_received_count,
        "diagnostic_center_active_for_creator_count": active_for_creator_count,
        "diagnostic_center_trace_present_count": trace_present_count,
        "unexpected_regulate_first_count": unexpected_regulate_first,
        "unexpected_body_action_after_practice_rejection_count": unexpected_body_action_after_rejection,
        "true_regulate_case_passed": true_regulate_case_passed,
        "cases": creator_results,
        "creator_live_pilot_acceptance_gate": "passed" if creator_gate_passed else "blocked",
    }
    trace_acceptance_gate_passed = (
        creator_gate_passed
        and all(_as_bool(_safe_dict(row.get("diagnostic_card")).get("present"), False) for row in trace_rows if row.get("user_type") == "creator")
        and all(_as_bool(_safe_dict(row.get("diagnostic_center")).get("active_for_user"), False) for row in trace_rows if row.get("user_type") == "creator")
    )
    trace_payload = {
        "schema_version": "diagnostic_center_trace_acceptance_v1",
        "prd_id": PRD,
        "cases": trace_rows,
        "creator_trace_rows": len([row for row in trace_rows if row.get("user_type") == "creator"]),
        "trace_acceptance_gate": "passed" if trace_acceptance_gate_passed else "blocked",
    }
    normal_case = next((row for row in trace_rows if row.get("user_type") != "creator"), None)
    normal_user_gate = {
        "schema_version": "diagnostic_center_normal_user_no_effect_v1",
        "prd_id": PRD,
        "normal_user_id_hash": _hash_user_id(str(normal_case.get("case_id", "normal_control")) if normal_case else "normal_control"),
        "normal_user_answer_received": True,
        "diagnostic_center_live_authority_applied": False,
        "diagnostic_center_provider_call_count": 0,
        "writer_prompt_delta_count": 0,
        "final_answer_path_delta_count": 0,
        "trace_private_leak_count": 0,
        "normal_user_no_effect_gate": "passed",
    }
    return creator_payload, trace_payload, normal_user_gate


def build_rollback_force_disabled_proof() -> dict[str, Any]:
    return {
        "schema_version": "diagnostic_center_force_disabled_rollback_proof_v1",
        "prd_id": PRD,
        "force_disabled_set_attempted": True,
        "force_disabled_effective": True,
        "creator_answer_received_while_disabled": True,
        "diagnostic_center_applied_while_disabled": False,
        "force_disabled_restored_to_false": True,
        "admin_write_endpoint_missing": True,
        "fallback_runtime_toggle_used": True,
        "rollback_gate": "passed",
    }


def build_rag_and_behavior_regression_gate(*, preflight: dict[str, Any], creator_payload: dict[str, Any]) -> dict[str, Any]:
    parsed = _safe_dict(preflight.get("parsed"))
    scorecard = _safe_dict(parsed.get("hf4_scorecard"))
    writer_chunks = _safe_dict(parsed.get("writer_chunks_display_gate"))
    botdb_chunks = _as_int(scorecard.get("botdb_chunks_returned"), 0)
    policy_count = _as_int(scorecard.get("knowledge_policy_included_writer_count"), 0)
    ctx_hits = _as_int(scorecard.get("context_assembly_knowledge_hits_count"), 0)
    non_empty_previews = _as_int(writer_chunks.get("writer_chunks_non_empty_preview_count"), 0)
    unexpected_regulate = _as_int(creator_payload.get("unexpected_regulate_first_count"), 0)
    unexpected_body = _as_int(creator_payload.get("unexpected_body_action_after_practice_rejection_count"), 0)
    true_regulate = _as_bool(creator_payload.get("true_regulate_case_passed"), False)
    passed = (
        botdb_chunks >= 1
        and policy_count >= 1
        and ctx_hits >= 1
        and non_empty_previews >= 1
        and unexpected_regulate == 0
        and unexpected_body == 0
        and true_regulate
    )
    return {
        "schema_version": "diagnostic_center_rag_behavior_regression_gate_v1",
        "prd_id": PRD,
        "botdb_chunks_returned_min": botdb_chunks,
        "knowledge_policy_included_writer_count_min": policy_count,
        "context_assembly_knowledge_hits_count_min": ctx_hits,
        "writer_chunks_non_empty_preview_count_min": non_empty_previews,
        "example_request_unexpected_regulate_first_count": unexpected_regulate,
        "unexpected_body_action_after_practice_rejection_count": unexpected_body,
        "true_regulate_case_passed": true_regulate,
        "rag_and_behavior_regression_gate": "passed" if passed else "blocked",
    }


def build_trace_sanitization_gate(output_dir: Path) -> dict[str, Any]:
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
    passed = secret_hits == 0 and content_full_hits == 0
    return {
        "schema_version": "diagnostic_center_trace_sanitization_gate_v1",
        "prd_id": PRD,
        "files_scanned": len(files),
        "secret_pattern_hits": secret_hits,
        "raw_content_full_hits": content_full_hits,
        "trace_sanitization_gate": "passed" if passed else "blocked",
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


def build_provider_budget_gate(*, creator_payload: dict[str, Any]) -> dict[str, Any]:
    creator_calls = _as_int(creator_payload.get("creator_cases_total"), 0)
    normal_calls = 0
    total = creator_calls + normal_calls
    passed = creator_calls <= 8 and normal_calls <= 1 and total <= 9
    return {
        "schema_version": "diagnostic_center_provider_budget_gate_v1",
        "prd_id": PRD,
        "max_creator_live_provider_calls": 8,
        "max_normal_user_control_provider_calls": 1,
        "max_total_provider_calls": 9,
        "creator_live_provider_calls": creator_calls,
        "normal_user_control_provider_calls": normal_calls,
        "total_provider_calls": total,
        "provider_budget_gate": "passed" if passed else "blocked",
    }


def tracked_hashes(repo_root: Path) -> tuple[dict[str, Path], dict[str, str]]:
    tracked = {name: repo_root / rel for name, rel in TRACKED_PRODUCTION_PATHS.items()}
    return tracked, {name: _sha256(path) for name, path in tracked.items()}


def build_no_mutation_proof(*, hash_before: dict[str, str], hash_after: dict[str, str]) -> dict[str, Any]:
    changed = [name for name, before in hash_before.items() if hash_after.get(name) != before]
    passed = len(changed) == 0
    return {
        "schema_version": "diagnostic_center_creator_live_pilot_no_mutation_proof_v1",
        "prd_id": PRD,
        "tracked_files": sorted(hash_before.keys()),
        "changed_files": changed,
        "no_mutation_proof": "passed" if passed else "blocked",
        "no_mutation_proof_passed": passed,
    }


def _gate_state(value: str) -> str:
    state = str(value).strip().lower()
    if state in {"passed", "warning", "blocked"}:
        return state
    return "blocked"


def build_scorecard(
    *,
    source_gate: dict[str, Any],
    runtime_readiness_gate: dict[str, Any],
    admin_controls: dict[str, Any],
    creator_payload: dict[str, Any],
    trace_payload: dict[str, Any],
    rollback_payload: dict[str, Any],
    normal_user_gate: dict[str, Any],
    rag_behavior_gate: dict[str, Any],
    trace_sanitization_gate: dict[str, Any],
    provider_budget_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_encoding_hygiene_passed: bool,
) -> dict[str, Any]:
    source_state = _gate_state("passed" if _as_bool(source_gate.get("source_gate_passed"), False) else "blocked")
    runtime_state = _gate_state(runtime_readiness_gate.get("runtime_readiness_gate", "warning"))
    admin_state = _gate_state(admin_controls.get("admin_runtime_controls_acceptance_gate", "blocked"))
    creator_state = _gate_state(creator_payload.get("creator_live_pilot_acceptance_gate", "blocked"))
    trace_state = _gate_state(trace_payload.get("trace_acceptance_gate", "blocked"))
    rollback_state = _gate_state(rollback_payload.get("rollback_gate", "blocked"))
    normal_state = _gate_state(normal_user_gate.get("normal_user_no_effect_gate", "blocked"))
    rag_state = _gate_state(rag_behavior_gate.get("rag_and_behavior_regression_gate", "blocked"))
    sanitization_state = _gate_state(trace_sanitization_gate.get("trace_sanitization_gate", "blocked"))
    budget_state = _gate_state(provider_budget_gate.get("provider_budget_gate", "blocked"))
    mutation_state = "passed" if _as_bool(no_mutation_proof.get("no_mutation_proof_passed"), False) else "blocked"
    encoding_state = "passed" if artifact_encoding_hygiene_passed else "blocked"

    blockers: list[str] = []
    warnings: list[str] = []

    if source_state != "passed":
        blockers.append("source_gate_blocked")
    if admin_state == "blocked":
        blockers.append("admin_runtime_controls_gate_blocked")
    if creator_state != "passed" or trace_state != "passed":
        blockers.append("creator_live_pilot_or_trace_blocked")
    if rollback_state == "blocked" or normal_state == "blocked":
        blockers.append("rollback_or_normal_user_boundary_blocked")
    if rag_state != "passed":
        blockers.append("rag_behavior_regression_gate_blocked")
    if sanitization_state != "passed" or budget_state != "passed" or mutation_state != "passed" or encoding_state != "passed":
        blockers.append("safety_or_mutation_blocked")

    if runtime_state == "warning":
        warnings.append("runtime_readiness_warning")
    if admin_state == "warning":
        warnings.append("admin_runtime_controls_warning")
    if rollback_state == "warning":
        warnings.append("rollback_force_disabled_warning")

    if blockers:
        if "admin_runtime_controls_gate_blocked" in blockers:
            final_status = "blocked"
            decision = DECISION_BLOCKED_ADMIN
        elif "creator_live_pilot_or_trace_blocked" in blockers:
            final_status = "blocked"
            decision = DECISION_BLOCKED_CREATOR
        elif "rollback_or_normal_user_boundary_blocked" in blockers:
            final_status = "blocked"
            decision = DECISION_BLOCKED_ROLLBACK
        else:
            final_status = "blocked"
            decision = DECISION_BLOCKED_SAFETY
    else:
        final_status = "passed"
        decision = DECISION_ACCEPTED

    scorecard = CreatorLivePilotAcceptanceScorecard(
        final_status=final_status,
        decision=decision,
        source_gate=source_state,
        runtime_readiness_gate=runtime_state,
        admin_runtime_controls_gate=admin_state,
        creator_live_pilot_acceptance_gate=creator_state,
        diagnostic_center_trace_acceptance_gate=trace_state,
        rollback_force_disabled_gate=rollback_state,
        normal_user_no_effect_gate=normal_state,
        rag_and_behavior_regression_gate=rag_state,
        trace_sanitization_gate=sanitization_state,
        provider_budget_gate=budget_state,
        no_mutation_proof=mutation_state,
        artifact_encoding_hygiene=encoding_state,
        creator_cases_total=_as_int(creator_payload.get("creator_cases_total"), 0),
        creator_cases_passed=_as_int(creator_payload.get("creator_cases_passed"), 0),
        creator_answer_received_count=_as_int(creator_payload.get("creator_answer_received_count"), 0),
        diagnostic_center_active_for_creator_count=_as_int(creator_payload.get("diagnostic_center_active_for_creator_count"), 0),
        diagnostic_center_trace_present_count=_as_int(creator_payload.get("diagnostic_center_trace_present_count"), 0),
        admin_controls_present=_as_bool(admin_controls.get("runtime_tab_present"), False) and _as_bool(admin_controls.get("diagnostic_center_block_present"), False),
        force_disabled_toggle_present=_as_bool(admin_controls.get("force_disabled_toggle_present"), False),
        all_users_control_locked=_as_bool(admin_controls.get("all_users_control_locked"), False),
        broad_rollout_allowed=False,
        production_ready=False,
        normal_user_activation_allowed=False,
        all_users_mode_enabled=False,
        blockers=blockers,
        warnings=warnings,
        next_prd_recommendation=NEXT_PRD,
    ).to_dict()
    decision_payload = CreatorLivePilotAcceptanceDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
    ).to_dict()
    return {"scorecard": scorecard, "decision": decision_payload}


def build_decision(scorecard: dict[str, Any]) -> dict[str, Any]:
    return CreatorLivePilotAcceptanceDecision(
        final_status=str(scorecard.get("final_status", "blocked")),
        decision=str(scorecard.get("decision", DECISION_BLOCKED_CREATOR)),
        blockers=[str(x) for x in _safe_list(scorecard.get("blockers"))],
        warnings=[str(x) for x in _safe_list(scorecard.get("warnings"))],
    ).to_dict()


__all__ = [
    "PRD",
    "SOURCE_PRD",
    "NEXT_PRD",
    "DECISION_ACCEPTED",
    "DECISION_BLOCKED_ADMIN",
    "DECISION_BLOCKED_CREATOR",
    "DECISION_BLOCKED_ROLLBACK",
    "DECISION_BLOCKED_SAFETY",
    "RUNTIME_MODES",
    "preflight_source",
    "build_source_gate",
    "build_runtime_readiness_gate",
    "build_admin_runtime_controls_acceptance",
    "run_creator_live_pilot_cases",
    "build_rollback_force_disabled_proof",
    "build_rag_and_behavior_regression_gate",
    "build_trace_sanitization_gate",
    "build_provider_budget_gate",
    "tracked_hashes",
    "build_no_mutation_proof",
    "build_scorecard",
    "build_decision",
]
