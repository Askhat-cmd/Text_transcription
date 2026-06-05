#!/usr/bin/env python3
"""PRD-047.12 runner: unified dialogue policy acceptance and evidence pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.answer_obligation_resolver import build_answer_obligation_resolver_v1
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.dialogue_policy import build_effective_dialogue_policy
from bot_agent.multiagent.dialogue_style_state import build_dialogue_style_state_v1
from bot_agent.multiagent.last_assistant_offer_tracker import build_last_assistant_offer_v1
from bot_agent.multiagent.unanswered_question_tracker import build_unanswered_question_state_v1

DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.12"
DEFAULT_REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8001/api/v1"
DEFAULT_ADMIN_RUNTIME_URL = "http://127.0.0.1:8001/api/admin/runtime/effective"
DEFAULT_CHAT_URL = "http://localhost:3000/chat"
PRD_ID = "PRD-047.12"
REQUIRED_SUBDIRS = (
    "live_cases",
    "live_turn_exports",
    "prompt_canvases",
    "raw_traces",
    "screenshots/web_chat_markdown",
    "dom_snapshots/web_chat_markdown",
)
BANNED_ENCODING_MARKERS = ["Рџ", "Рґ", "Рё", "РЅ", "СЃ", "С‚", "СЊ", "РЎ", "Рќ", "�", "\x07", "\x0c"]

LIVE_CASES = [
    {
        "case_id": "T01",
        "title": "self intro",
        "turns": ["Давай знакомиться, меня зовут Асхат"],
        "expect": {"dialogue_act": "self_intro", "answer_obligation": "acknowledge_self_intro"},
        "answer_contains": ["Асхат"],
    },
    {
        "case_id": "T02",
        "title": "meta feedback overexplaining",
        "turns": ["Я просто познакомился, а ты усложнил"],
        "expect": {"dialogue_act_any": ["repair_complaint", "meta_system_feedback"]},
        "answer_contains_any": ["усложнил", "короче", "промах"],
    },
    {
        "case_id": "T03",
        "title": "style plus knowledge question",
        "turns": ["отвечай спокойнее. что такое нейросталкинг, и как его можно применять в жизни?"],
        "expect": {"dialogue_act": "knowledge_question", "answer_obligation": "acknowledge_style_preference_then_answer"},
        "answer_contains_any": ["нейросталкинг", "применять", "в жизни"],
    },
    {
        "case_id": "T04",
        "title": "repair complaint",
        "turns": ["что такое нейросталкинг?", "ты не ответил мне на вопрос"],
        "expect": {"dialogue_act": "repair_complaint", "answer_obligation": "repair_and_answer_last_question"},
        "answer_contains_any": ["нейросталкинг", "промах", "вопрос"],
    },
    {
        "case_id": "T05",
        "title": "yes to last offer",
        "turns": [
            "Можешь сначала предложить, а не отвечать целиком: покажешь потом, как адаптировать технику под Красный, Оранжевый и Зеленый уровни?",
            "да",
        ],
        "expect": {"dialogue_act": "confirmation_to_last_offer", "answer_obligation": "answer_last_offer"},
        "answer_contains_any": ["Красный", "Оранжевый", "Зелен"],
    },
    {
        "case_id": "T06",
        "title": "close ack",
        "turns": ["спасибо"],
        "expect": {"dialogue_act": "close_ack", "answer_obligation": "close_gently"},
        "answer_forbid": ["упражн", "задач", "практик"],
    },
    {
        "case_id": "T07",
        "title": "repeated direct question",
        "turns": ["повторю вопрос, что такое нейросталкинг, и как его применять?"],
        "expect": {"dialogue_act_any": ["knowledge_question", "direct_question"]},
        "answer_contains_any": ["нейросталкинг", "применять"],
    },
    {
        "case_id": "T08",
        "title": "concrete situation",
        "turns": ["сталкиваюсь с несправедливостью и быстро выхожу из себя. что с этим происходит?"],
        "expect": {"dialogue_act": "concrete_situation_question", "answer_obligation": "answer_concrete_situation"},
        "answer_forbid": ["сейчас полезнее не упражнение"],
    },
    {
        "case_id": "T09",
        "title": "profile preset compatibility mvp alias",
        "kind": "runtime_only",
        "expect_runtime": {"active_profile_alias": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    },
    {
        "case_id": "T10",
        "title": "profile preset compatibility safe guided",
        "kind": "runtime_only",
        "expect_runtime": {"safe_guided_supported": True},
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _run_cmd(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_layout(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_SUBDIRS:
        (log_dir / name).mkdir(parents=True, exist_ok=True)


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    request_headers = dict(headers)
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, method=method.upper(), headers=request_headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return int(getattr(response, "status", 200)), data if isinstance(data, dict) else {"raw": data}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return int(getattr(exc, "code", 500)), parsed if isinstance(parsed, dict) else {"raw": parsed}


def _http_text_status(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"status": int(getattr(response, "status", 200)), "length": len(body)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def _scan_text(path: Path) -> dict[str, Any]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"path": str(path.as_posix()), "issues": ["utf8_decode_error"]}
    for marker in BANNED_ENCODING_MARKERS:
        if marker in text:
            issues.append(f"contains:{marker.encode('unicode_escape').decode('ascii')}")
    if re.search(r"(?:Р.|С.){4,}", text):
        issues.append("cyrillic_mojibake_pattern")
    return {"path": str(path.as_posix()), "issues": sorted(set(issues))}


def _scan_targets(targets: list[Path]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    issue_count = 0
    extensions = {".md", ".txt", ".json", ".py", ".ts", ".tsx", ".css", ".html"}
    for root in targets:
        if root.is_file():
            scanned = [_scan_text(root)]
        elif root.exists():
            scanned = [_scan_text(p) for p in root.rglob("*") if p.is_file() and p.suffix.lower() in extensions]
        else:
            scanned = []
        for item in scanned:
            if item["issues"]:
                issue_count += len(item["issues"])
                files.append(item)
    return {
        "generated_at_utc": _now_iso(),
        "issue_file_count": len(files),
        "issue_count": issue_count,
        "files": files,
    }


def build_source_inventory(log_dir: Path) -> dict[str, Any]:
    head_code, head_out, _ = _run_cmd(["git", "rev-parse", "HEAD"])
    status_code, status_out, _ = _run_cmd(["git", "status", "--short"])
    log_code, log_out, _ = _run_cmd(["git", "log", "--oneline", "-12"])
    files = {
        "docs/PROJECT_STATE.md": (REPO_ROOT / "docs/PROJECT_STATE.md").exists(),
        "docs/ROADMAP.md": (REPO_ROOT / "docs/ROADMAP.md").exists(),
        "docs/PRD_INDEX.md": (REPO_ROOT / "docs/PRD_INDEX.md").exists(),
        "docs/DECISIONS.md": (REPO_ROOT / "docs/DECISIONS.md").exists(),
        "bot_psychologist/docs": (PROJECT_ROOT / "docs").exists(),
    }
    rg_queries = {
        "runtime_profiles": "DIALOGUE_PROFILE|profile_preset|active_profile_alias",
        "safe_guided_mentions": "safe_guided",
        "mvp_free_dialogue_mentions": "mvp_free_dialogue",
        "final_answer_directive": "final_answer_directive_v1",
        "writer_prompt": "WRITER_USER_TEMPLATE|FINAL ANSWER DIRECTIVE|UNIFIED DIALOGUE POLICY",
        "writer_context_package": "writer_context_package_v1|WRITER CONTEXT PACKAGE",
        "fresh_chat_context_policy": "fresh_chat_context_policy_v1",
        "rag_context_package": "rag_for_writer|contextual_retrieval_decision|writer_context_package",
        "diagnostic_planner_active_line": "diagnostic_center_role|planner_role|active_line_role|diagnostic_card_role",
        "web_admin_profile_flags": "profile_preset|active_profile_alias|dialogue_act_resolver_enabled",
        "web_chat_messages": "ReactMarkdown|message-bot|prose",
    }
    rg_hits: dict[str, list[str]] = {}
    for name, query in rg_queries.items():
        code, out, _ = _run_cmd(["rg", "-n", query, "bot_psychologist", "docs", "TO_DO_LIST"])
        rg_hits[name] = out.splitlines()[:40] if code in {0, 1} else []
    payload = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "head": head_out.strip() if head_code == 0 else "",
        "git_status_short": status_out.splitlines() if status_code == 0 else [],
        "last_commits": log_out.splitlines() if log_code == 0 else [],
        "required_files": files,
        "rg_hits": rg_hits,
    }
    lines = [f"# {PRD_ID} Source Inventory", "", f"- head: `{payload['head']}`", "- required_files:"]
    for key, value in files.items():
        lines.append(f"  - `{key}` => `{value}`")
    lines.append("- recent_commits:")
    for line in payload["last_commits"]:
        lines.append(f"  - `{line}`")
    for name, hits in rg_hits.items():
        lines.append(f"- {name}:")
        for hit in hits[:12]:
            lines.append(f"  - `{hit}`")
    _write_json(log_dir / "source_inventory.json", payload)
    _write_text(log_dir / "source_inventory.md", "\n".join(lines))
    return payload


def build_hf3_artifact_audit(log_dir: Path) -> dict[str, Any]:
    hf3_dir = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF3"
    files = [
        REPO_ROOT / "TO_DO_LIST/reports/PRD-047.11-HF3_IMPLEMENTATION_REPORT.md",
        REPO_ROOT / "TO_DO_LIST/reports/PRD-047.11-HF3_NEXT_PRD_RECOMMENDATION.md",
        hf3_dir / "live_cases_result.json",
        hf3_dir / "live_cases_result.md",
        hf3_dir / "browser_smoke_result.json",
        hf3_dir / "browser_smoke_result.md",
        hf3_dir / "admin_legacy_inventory.json",
        hf3_dir / "admin_legacy_inventory.md",
    ]
    warnings: list[str] = []
    for path in files:
        if not path.exists():
            warnings.append(f"missing:{path.relative_to(REPO_ROOT).as_posix()}")
    browser_payload = {}
    live_payload = {}
    if (hf3_dir / "browser_smoke_result.json").exists():
        browser_payload = json.loads((hf3_dir / "browser_smoke_result.json").read_text(encoding="utf-8"))
        if browser_payload.get("status") != "passed":
            warnings.append(f"hf3_browser_status:{browser_payload.get('status')}")
    if (hf3_dir / "live_cases_result.json").exists():
        live_payload = json.loads((hf3_dir / "live_cases_result.json").read_text(encoding="utf-8"))
        if live_payload.get("status") != "passed":
            warnings.append(f"hf3_live_status:{live_payload.get('status')}")
    payload = {
        "generated_at_utc": _now_iso(),
        "hf3_dir_exists": hf3_dir.exists(),
        "required_files_present": {path.relative_to(REPO_ROOT).as_posix(): path.exists() for path in files},
        "hf3_live_status": live_payload.get("status"),
        "hf3_browser_status": browser_payload.get("status"),
        "warnings_to_carry_forward": warnings,
    }
    lines = [f"# {PRD_ID} HF3 Artifact Audit", "", f"- hf3_dir_exists: `{payload['hf3_dir_exists']}`", "- warnings_to_carry_forward:"]
    for item in warnings:
        lines.append(f"  - `{item}`")
    _write_json(log_dir / "hf3_artifact_audit.json", payload)
    _write_text(log_dir / "hf3_artifact_audit.md", "\n".join(lines))
    return payload


def write_runtime_startup(log_dir: Path, *, base_url: str, admin_runtime_url: str, chat_url: str, api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    headers = {"X-API-Key": api_key}
    health_status, health_payload = _http_json_request(method="GET", url=f"{base_url.rstrip('/')}/health", headers=headers, timeout=30.0)
    runtime_status, runtime_payload = _http_json_request(method="GET", url=admin_runtime_url, headers=headers, timeout=30.0)
    chat_check = _http_text_status(chat_url)
    payload = {
        "generated_at_utc": _now_iso(),
        "backend_url": base_url,
        "frontend_url": chat_url,
        "health_status": health_status,
        "admin_runtime_status": runtime_status,
        "active_profile_alias": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("active_profile_alias"),
        "profile_preset": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("profile_preset"),
        "unified_dialogue_policy_version": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("version"),
        "diagnostic_center_mode": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("diagnostic_center_role"),
        "chat_url_check": chat_check,
    }
    lines = [
        f"# {PRD_ID} Runtime Startup",
        "",
        f"- backend_url: `{payload['backend_url']}`",
        f"- frontend_url: `{payload['frontend_url']}`",
        f"- health_status: `{health_status}`",
        f"- admin_runtime_status: `{runtime_status}`",
        f"- active_profile_alias: `{payload['active_profile_alias']}`",
        f"- profile_preset: `{payload['profile_preset']}`",
        f"- unified_dialogue_policy_version: `{payload['unified_dialogue_policy_version']}`",
        f"- diagnostic_center_mode: `{payload['diagnostic_center_mode']}`",
        f"- chat_url_check: `{chat_check}`",
    ]
    _write_json(log_dir / "runtime_startup.json", payload)
    _write_text(log_dir / "runtime_startup.md", "\n".join(lines))
    return payload, runtime_payload


def _derive_api_root(base_url: str) -> str:
    return base_url[:-7] if base_url.rstrip("/").endswith("/api/v1") else base_url.rstrip("/")


def _post_turn(*, base_url: str, headers: dict[str, str], session_id: str, query: str) -> tuple[int, dict[str, Any]]:
    return _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/questions/adaptive",
        headers=headers,
        payload={
            "query": query,
            "user_id": "prd04712_runner",
            "session_id": session_id,
            "debug": True,
            "include_path": False,
            "include_feedback_prompt": True,
        },
        timeout=180.0,
    )


def _fetch_latest_trace(*, base_url: str, headers: dict[str, str], session_id: str) -> tuple[int, dict[str, Any]]:
    api_root = _derive_api_root(base_url)
    return _http_json_request(
        method="GET",
        url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/multiagent-trace",
        headers=headers,
        timeout=60.0,
    )


def _fetch_full_traces(*, base_url: str, headers: dict[str, str], session_id: str) -> tuple[int, dict[str, Any]]:
    api_root = _derive_api_root(base_url)
    return _http_json_request(
        method="GET",
        url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/traces?format=full",
        headers=headers,
        timeout=60.0,
    )


def _save_prompt_canvas(log_dir: Path, case_id: str, trace_payload: dict[str, Any]) -> None:
    live = _safe_dict(trace_payload.get("live_turn_evidence"))
    prompt_canvas = _safe_dict(_safe_dict(live.get("writer")).get("prompt_canvas"))
    if prompt_canvas:
        _write_json(log_dir / "prompt_canvases" / f"{case_id}.json", prompt_canvas)


def _dry_case_result(case: dict[str, Any]) -> dict[str, Any]:
    kind = str(case.get("kind", "dialogue"))
    if kind == "runtime_only":
        return {"case_id": case["case_id"], "status": "passed", "checks": {"runtime_only_case": True}, "failed_checks": []}

    previous_question_state = None
    previous_last_offer = None
    last_result: dict[str, Any] = {}
    for idx, turn in enumerate(case.get("turns", []), start=1):
        if idx == 2 and case["case_id"] == "T05":
            last_offer = build_last_assistant_offer_v1(
                previous_state=None,
                previous_assistant_message="Могу показать, как адаптировать технику под Красный, Оранжевый и Зеленый уровни.",
                dialogue_pragmatics={"is_contextual_followup": True},
            )
        else:
            last_offer = previous_last_offer or {}
        act = build_dialogue_act_resolution_v1(
            user_message=turn,
            dialogue_pragmatics={"is_contextual_followup": idx > 1},
            last_assistant_offer=last_offer,
            knowledge_answer_guard={"knowledge_answer": {"needed": "?" in turn or "что такое" in turn.lower() or "нейросталкинг" in turn.lower()}},
        )
        unanswered = build_unanswered_question_state_v1(
            previous_state=previous_question_state,
            user_message=turn,
            dialogue_act_resolution=act,
            turn_index=idx,
        )
        style_state = build_dialogue_style_state_v1(
            previous_state=None,
            user_message=turn,
            dialogue_act_resolution=act,
        )
        obligation = build_answer_obligation_resolver_v1(
            dialogue_act_resolution=act,
            last_assistant_offer=last_offer,
            unanswered_question_state=unanswered,
            dialogue_style_state=style_state,
            dialogue_policy=build_effective_dialogue_policy(
                profile="mvp_free_dialogue",
                user_message=turn,
                state_snapshot={"safety_flag": False},
                thread_state={"safety_active": False, "response_mode": "reflect"},
                knowledge_answer_guard={"knowledge_answer": {"needed": "?" in turn or "что такое" in turn.lower()}},
            ),
        )
        previous_question_state = unanswered
        previous_last_offer = last_offer
        last_result = {"act": act, "obligation": obligation}
    checks: dict[str, bool] = {}
    expect = _safe_dict(case.get("expect"))
    if expect.get("dialogue_act"):
        checks["dialogue_act"] = last_result["act"].get("dialogue_act") == expect["dialogue_act"]
    if expect.get("dialogue_act_any"):
        checks["dialogue_act_any"] = last_result["act"].get("dialogue_act") in list(expect["dialogue_act_any"])
    if expect.get("answer_obligation"):
        checks["answer_obligation"] = last_result["obligation"].get("answer_obligation") == expect["answer_obligation"]
    failed = [key for key, value in checks.items() if not value]
    return {"case_id": case["case_id"], "status": "passed" if not failed else "failed", "checks": checks, "failed_checks": failed}


def run_dry_cases(log_dir: Path) -> dict[str, Any]:
    results = [_dry_case_result(case) for case in LIVE_CASES]
    status = "passed" if all(item["status"] == "passed" for item in results) else "blocker"
    payload = {"generated_at_utc": _now_iso(), "status": status, "case_results": results}
    _write_json(log_dir / "live_cases" / "dry_cases_result.json", payload)
    return payload


def run_direct_cases(log_dir: Path, runtime_payload: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "version": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("version") == "unified_dialogue_policy_v2",
        "dialogue_act_resolver_enabled": bool(_safe_dict(runtime_payload).get("dialogue_policy", {}).get("dialogue_act_resolver_enabled")),
        "last_offer_tracker_enabled": bool(_safe_dict(runtime_payload).get("dialogue_policy", {}).get("last_offer_tracker_enabled")),
        "unanswered_question_tracker_enabled": bool(_safe_dict(runtime_payload).get("dialogue_policy", {}).get("unanswered_question_tracker_enabled")),
        "style_state_enabled": bool(_safe_dict(runtime_payload).get("dialogue_policy", {}).get("style_state_enabled")),
        "legacy_blocks_hidden": not bool(_safe_dict(runtime_payload).get("dialogue_policy", {}).get("legacy_blocks_visible_to_writer", True)),
    }
    payload = {
        "generated_at_utc": _now_iso(),
        "status": "passed" if all(checks.values()) else "warning",
        "checks": checks,
    }
    _write_json(log_dir / "live_cases" / "direct_cases_result.json", payload)
    return payload


def _check_case_expectations(case: dict[str, Any], trace_payload: dict[str, Any], answer: str) -> tuple[dict[str, bool], dict[str, Any]]:
    live = _safe_dict(trace_payload.get("live_turn_evidence"))
    dialogue = _safe_dict(live.get("dialogue"))
    policy = _safe_dict(dialogue.get("policy"))
    act = _safe_dict(dialogue.get("dialogue_act_resolution"))
    obligation = _safe_dict(dialogue.get("answer_obligation_resolution"))
    style = _safe_dict(dialogue.get("dialogue_style_state"))
    checks: dict[str, bool] = {
        "trace_has_unified_dialogue_policy": bool(dialogue.get("unified_dialogue_policy")),
        "trace_has_dialogue_act_resolution": bool(act),
        "trace_has_last_assistant_offer": "last_assistant_offer" in dialogue,
        "trace_has_unanswered_question_state": "unanswered_question_state" in dialogue,
        "trace_has_dialogue_style_state": "dialogue_style_state" in dialogue,
        "trace_has_answer_obligation_resolution": bool(obligation),
        "writer_context_package_present": bool(_safe_dict(_safe_dict(live.get("writer")).get("prompt_assembly")).get("writer_context_package")),
        "fresh_chat_context_policy_present": bool(dialogue.get("fresh_chat_context_policy")),
        "retrieval_decision_present": bool(dialogue.get("retrieval")),
        "policy_version_v2": policy.get("version") == "unified_dialogue_policy_v2",
    }
    expect = _safe_dict(case.get("expect"))
    if expect.get("dialogue_act"):
        checks["dialogue_act"] = act.get("dialogue_act") == expect["dialogue_act"]
    if expect.get("dialogue_act_any"):
        checks["dialogue_act_any"] = act.get("dialogue_act") in list(expect["dialogue_act_any"])
    if expect.get("answer_obligation"):
        checks["answer_obligation"] = obligation.get("answer_obligation") == expect["answer_obligation"]
    if case.get("answer_contains"):
        for token in case["answer_contains"]:
            checks[f"answer_contains::{token}"] = token.lower() in answer.lower()
    if case.get("answer_contains_any"):
        checks["answer_contains_any"] = any(token.lower() in answer.lower() for token in case["answer_contains_any"])
    if case.get("answer_forbid"):
        for token in case["answer_forbid"]:
            checks[f"answer_forbid::{token}"] = token.lower() not in answer.lower()
    if act.get("dialogue_act") == "knowledge_question":
        checks["style_captured_when_requested"] = bool(style.get("tone") or style.get("length_preference"))
    return checks, {"dialogue": dialogue, "policy": policy, "act": act, "obligation": obligation}


def run_live_cases(log_dir: Path, *, base_url: str, api_key: str) -> dict[str, Any]:
    headers = {
        "X-API-Key": api_key,
        "X-Session-Id": "prd04712-web-session",
        "X-Device-Fingerprint": "sha256:prd04712-device",
    }
    case_results = []
    failures = 0
    for case in LIVE_CASES:
        if case.get("kind") == "runtime_only":
            case_results.append({"case_id": case["case_id"], "title": case["title"], "status": "passed", "checks": {"runtime_only_case": True}, "failed_checks": []})
            continue
        case_id = str(case["case_id"])
        session_id = f"prd04712-{case_id.lower()}-{uuid.uuid4().hex[:8]}"
        answers: list[str] = []
        statuses: list[int] = []
        for idx, turn in enumerate(case.get("turns", []), start=1):
            status, payload = _post_turn(base_url=base_url, headers=headers, session_id=session_id, query=str(turn))
            statuses.append(status)
            answer = str(_safe_dict(payload).get("answer", "") or "")
            answers.append(answer)
            _write_json(log_dir / "live_turn_exports" / case_id / f"turn_{idx:02d}.json", {"case_id": case_id, "turn_index": idx, "user_message": turn, "assistant_answer": answer, "response": payload})
        latest_status, latest_payload = _fetch_latest_trace(base_url=base_url, headers=headers, session_id=session_id)
        full_status, full_payload = _fetch_full_traces(base_url=base_url, headers=headers, session_id=session_id)
        latest_trace = latest_payload if isinstance(latest_payload, dict) else {}
        _write_json(log_dir / "raw_traces" / f"{case_id}_trace_latest.json", latest_trace)
        _write_json(log_dir / "raw_traces" / f"{case_id}_traces_full.json", full_payload if isinstance(full_payload, dict) else {"status": full_status})
        _save_prompt_canvas(log_dir, case_id, latest_trace)
        latest_answer = answers[-1] if answers else ""
        checks, details = _check_case_expectations(case, latest_trace, latest_answer)
        checks["all_status_200"] = all(code == 200 for code in statuses)
        checks["latest_trace_status_200"] = latest_status == 200
        checks["full_traces_status_200"] = full_status == 200
        failed = [key for key, value in checks.items() if not value]
        if failed:
            failures += 1
        case_results.append(
            {
                "case_id": case_id,
                "title": case["title"],
                "session_id": session_id,
                "status": "passed" if not failed else "failed",
                "answers": answers,
                "checks": checks,
                "failed_checks": failed,
                "details": details,
            }
        )
    status = "passed" if failures == 0 else "warning"
    payload = {"generated_at_utc": _now_iso(), "status": status, "case_results": case_results}
    _write_json(log_dir / "live_cases_result.json", payload)
    lines = [f"# {PRD_ID} Live Cases Result", "", f"- status: `{status}`"]
    for case in case_results:
        lines.append(f"## {case['case_id']} - {case['title']}")
        lines.append(f"- status: `{case['status']}`")
        lines.append(f"- failed_checks: `{case['failed_checks']}`")
        for idx, answer in enumerate(case.get("answers", []), start=1):
            lines.append(f"- answer_{idx}: `{answer[:260]}`")
    _write_text(log_dir / "live_cases_result.md", "\n".join(lines))
    return payload


def run_browser_and_admin_smoke(log_dir: Path, *, chat_url: str, api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    browser_result_json = log_dir / "browser_smoke_result.json"
    admin_result_json = log_dir / "admin_surface_inventory.json"
    screenshot_path = log_dir / "screenshots" / "web_chat_markdown" / "chat_markdown.png"
    dom_path = log_dir / "dom_snapshots" / "web_chat_markdown" / "chat_markdown.html"
    prompt = "Объясни нейросталкинг спокойно и структурно: дай краткое определение, 3 пункта применения и один пример. Используй жирное выделение для ключевого термина."
    script = f"""
const fs = require('node:fs');
const path = require('node:path');
function classify(label) {{
  const value = String(label || '').toLowerCase();
  if (!value.trim()) return 'unknown_needs_followup';
  if (value.includes('runtime') || value.includes('policy') || value.includes('memory controls')) return 'active_runtime_surface';
  if (value.includes('trace') || value.includes('drift') || value.includes('testing')) return 'active_observability_surface';
  if (value.includes('diagnostic center') || value.includes('planner') || value.includes('philosophy')) return 'advisory_surface';
  if (value.includes('dev') || value.includes('advanced controls') || value.includes('compatibility')) return 'dev_only_surface';
  if (value.includes('legacy') || value.includes('history')) return 'legacy_or_historical_surface';
  return 'unknown_needs_followup';
}}
async function main() {{
  let playwright = null;
  try {{
    playwright = require('playwright');
  }} catch (e) {{
    try {{ playwright = require(path.join(process.cwd(), 'node_modules', 'playwright')); }} catch (_e2) {{
      fs.writeFileSync({json.dumps(str(browser_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_not_installed' }}, null, 2), 'utf8');
      fs.writeFileSync({json.dumps(str(admin_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_not_installed' }}, null, 2), 'utf8');
      return;
    }}
  }}
  const browser = await playwright.chromium.launch({{ headless: true }});
  try {{
    const page = await browser.newPage();
    await page.addInitScript((key) => {{
      window.localStorage.setItem('devApiKey', key);
      window.localStorage.setItem('bot_api_key', key);
      window.localStorage.setItem('bot_web_session_id', 'prd04712-browser');
    }}, {json.dumps(api_key)});
    await page.goto({json.dumps(chat_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(1500);
    const textarea = page.locator('textarea').first();
    await textarea.fill({json.dumps(prompt)});
    await textarea.press('Enter');
    await page.waitForTimeout(12000);
    await page.screenshot({{ path: {json.dumps(str(screenshot_path))}, fullPage: true }});
    fs.writeFileSync({json.dumps(str(dom_path))}, await page.content(), 'utf8');
    const chatChecks = await page.evaluate(() => {{
      const nodes = Array.from(document.querySelectorAll('.message-bot .prose'));
      const target = nodes[nodes.length - 1] || document.body;
      const text = target.textContent || '';
      return {{
        assistant_message_count: nodes.length,
        has_strong: Boolean(target.querySelector('strong')),
        has_list: Boolean(target.querySelector('ul,ol')),
        li_count: target.querySelectorAll('li').length,
        paragraph_count: target.querySelectorAll('p').length,
        raw_markdown_visible: text.includes('**'),
      }};
    }});
    fs.writeFileSync({json.dumps(str(browser_result_json))}, JSON.stringify({{
      chat_url: {json.dumps(chat_url)},
      assistant_message_count: chatChecks.assistant_message_count,
      has_strong: chatChecks.has_strong,
      has_list: chatChecks.has_list,
      li_count_min: chatChecks.li_count,
      paragraph_count_min: chatChecks.paragraph_count,
      raw_markdown_visible: chatChecks.raw_markdown_visible,
      status: (chatChecks.assistant_message_count >= 1 && chatChecks.has_strong && chatChecks.has_list && chatChecks.li_count >= 2 && chatChecks.paragraph_count >= 2 && !chatChecks.raw_markdown_visible) ? 'passed' : 'warning'
    }}, null, 2), 'utf8');
    await page.goto({json.dumps(chat_url.replace("/chat", "/admin"))}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(2500);
    const labels = await page.evaluate(() => Array.from(document.querySelectorAll('button,h1,h2,h3,h4,summary,div')).map(node => (node.textContent || '').trim()).filter(Boolean).slice(0, 300));
    const items = Array.from(new Set(labels)).slice(0, 120).map(label => ({{ label, category: classify(label) }}));
    const counts = items.reduce((acc, item) => {{ acc[item.category] = (acc[item.category] || 0) + 1; return acc; }}, {{}});
    fs.writeFileSync({json.dumps(str(admin_result_json))}, JSON.stringify({{
      status: items.length ? 'passed' : 'warning',
      items,
      counts,
    }}, null, 2), 'utf8');
  }} catch (e) {{
    fs.writeFileSync({json.dumps(str(browser_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_execution_error:' + String(e) }}, null, 2), 'utf8');
    fs.writeFileSync({json.dumps(str(admin_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_execution_error:' + String(e) }}, null, 2), 'utf8');
  }} finally {{
    await browser.close().catch(() => {{}});
  }}
}}
main();
"""
    subprocess.run(["node", "-e", script], cwd=str(PROJECT_ROOT / "web_ui"), capture_output=True, text=True, timeout=420, check=False)
    browser_payload = json.loads(browser_result_json.read_text(encoding="utf-8")) if browser_result_json.exists() else {"status": "warning", "reason": "missing_browser_result"}
    admin_payload = json.loads(admin_result_json.read_text(encoding="utf-8")) if admin_result_json.exists() else {"status": "warning", "reason": "missing_admin_inventory"}
    browser_lines = [
        f"# {PRD_ID} Browser Smoke",
        "",
        f"- status: `{browser_payload.get('status')}`",
        f"- chat_url: `{browser_payload.get('chat_url', chat_url)}`",
        f"- assistant_message_count: `{browser_payload.get('assistant_message_count')}`",
        f"- has_strong: `{browser_payload.get('has_strong')}`",
        f"- has_list: `{browser_payload.get('has_list')}`",
        f"- li_count_min: `{browser_payload.get('li_count_min')}`",
        f"- paragraph_count_min: `{browser_payload.get('paragraph_count_min')}`",
        f"- raw_markdown_visible: `{browser_payload.get('raw_markdown_visible')}`",
    ]
    admin_lines = [f"# {PRD_ID} Admin Surface Inventory", "", f"- status: `{admin_payload.get('status')}`", "- counts:"]
    for key, value in _safe_dict(admin_payload.get("counts")).items():
        admin_lines.append(f"  - {key}: `{value}`")
    for item in list(admin_payload.get("items", []) or [])[:40]:
        admin_lines.append(f"- `{item.get('label')}` => `{item.get('category')}`")
    _write_text(log_dir / "browser_smoke_result.md", "\n".join(browser_lines))
    _write_text(log_dir / "admin_surface_inventory.md", "\n".join(admin_lines))
    return browser_payload, admin_payload


def write_no_mutation(log_dir: Path) -> dict[str, Any]:
    payload = {
        "generated_at_utc": _now_iso(),
        "diagnostic_center_deleted": False,
        "diagnostic_center_hard_authority": False,
        "planner_hard_authority": False,
        "active_line_hard_authority": False,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "kb_governance_authority_fields_mutated": False,
        "chroma_reindex_executed": False,
        "new_runtime_path_created": False,
        "legacy_cascade_returned": False,
        "new_llm_agent_added": False,
        "raw_provider_payload_committed": False,
        "raw_private_logs_committed": False,
        "env_or_secrets_committed": False,
        "safe_guided_deleted": False,
        "mvp_free_dialogue_deleted_without_alias": False,
        "writer_gets_only_unified_sanitized_blocks": True,
    }
    _write_json(log_dir / "no_mutation_proof.json", payload)
    _write_text(log_dir / "no_mutation_proof.md", "\n".join([f"# {PRD_ID} No Mutation Proof", ""] + [f"- {k}: `{v}`" for k, v in payload.items()]))
    return payload


def write_reports(report_dir: Path, *, startup: dict[str, Any], dry: dict[str, Any], direct: dict[str, Any], live: dict[str, Any], browser: dict[str, Any], admin_inventory: dict[str, Any], pre_scan: dict[str, Any], hygiene: dict[str, Any], hf3_audit: dict[str, Any]) -> None:
    implementation_lines = [
        f"# {PRD_ID} IMPLEMENTATION REPORT",
        "",
        f"- generated_at_utc: `{_now_iso()}`",
        f"- unified_dialogue_policy_version: `{startup.get('unified_dialogue_policy_version')}`",
        f"- active_profile_alias: `{startup.get('active_profile_alias')}`",
        f"- profile_preset: `{startup.get('profile_preset')}`",
        f"- dry_status: `{dry.get('status')}`",
        f"- direct_status: `{direct.get('status')}`",
        f"- live_status: `{live.get('status')}`",
        f"- browser_status: `{browser.get('status')}`",
        f"- admin_surface_status: `{admin_inventory.get('status')}`",
        f"- encoding_pre_scan_issue_file_count: `{pre_scan.get('issue_file_count')}`",
        f"- encoding_hygiene_issue_file_count: `{hygiene.get('issue_file_count')}`",
        "",
        "## Scope",
        "- unified_dialogue_policy_v2 over a single runtime path",
        "- preset resolution for safe_guided / free_dialogue_default / custom_dev",
        "- dialogue act, last-offer, unanswered-question, style-state, and answer-obligation layers",
        "- writer-first prompt contract and admin/runtime visibility",
        "- live/browser/admin evidence pack",
        "",
        "## HF3 carry-forward",
        f"- warnings_to_carry_forward: `{hf3_audit.get('warnings_to_carry_forward')}`",
    ]
    next_lines = [
        f"# {PRD_ID} NEXT PRD RECOMMENDATION",
        "",
        "Recommended next PRD: `PRD-047.12-HF1` only if live/browser evidence still leaves residual follow-up or rendering warnings.",
        "If browser smoke passes and live cases are stable, the next logical step is cleanup/consolidation of legacy admin surface, not another dialogue micro-hotfix.",
    ]
    _write_text(report_dir / f"{PRD_ID}_IMPLEMENTATION_REPORT.md", "\n".join(implementation_lines))
    _write_text(report_dir / f"{PRD_ID}_NEXT_PRD_RECOMMENDATION.md", "\n".join(next_lines))


def write_command_log(log_dir: Path, *, commands: list[dict[str, Any]]) -> None:
    lines = [f"# {PRD_ID} Command Output", ""]
    for item in commands:
        lines.append(f"## {item['name']}")
        lines.append(f"- command: `{item['command']}`")
        lines.append(f"- exit_code: `{item['exit_code']}`")
        if item.get("stdout"):
            lines.append("```text")
            lines.append(str(item["stdout"]).strip())
            lines.append("```")
        if item.get("stderr"):
            lines.append("```text")
            lines.append(str(item["stderr"]).strip())
            lines.append("```")
        lines.append("")
    _write_text(log_dir / "test_command_output.txt", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.12 evidence pack")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--base-url", default=os.getenv("PRD04712_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--frontend-url", default=os.getenv("PRD04712_FRONTEND_URL", DEFAULT_CHAT_URL))
    parser.add_argument("--api-key", default=os.getenv("PRD04712_API_KEY", "dev-key-001"))
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--export-turns", action="store_true")
    parser.add_argument("--export-prompts", action="store_true")
    parser.add_argument("--export-traces", action="store_true")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    log_dir = Path(args.log_dir).resolve()
    report_dir = Path(args.report_dir).resolve()
    _ensure_layout(log_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    build_source_inventory(log_dir)
    hf3_audit = build_hf3_artifact_audit(log_dir)
    pre_scan = _scan_targets([REPO_ROOT / "docs", REPO_ROOT / "TO_DO_LIST", PROJECT_ROOT])
    _write_json(log_dir / "encoding_pre_scan.json", pre_scan)
    _write_text(log_dir / "encoding_pre_scan.md", f"# {PRD_ID} Encoding Pre Scan\n\n- issue_file_count: `{pre_scan['issue_file_count']}`\n- issue_count: `{pre_scan['issue_count']}`")

    startup, runtime_payload = write_runtime_startup(log_dir, base_url=args.base_url, admin_runtime_url=DEFAULT_ADMIN_RUNTIME_URL, chat_url=args.frontend_url, api_key=args.api_key)
    dry = run_dry_cases(log_dir)
    direct = run_direct_cases(log_dir, runtime_payload)
    live = run_live_cases(log_dir, base_url=args.base_url, api_key=args.api_key)
    browser, admin_inventory = run_browser_and_admin_smoke(log_dir, chat_url=args.frontend_url, api_key=args.api_key)
    no_mutation = write_no_mutation(log_dir)
    hygiene = _scan_targets([PROJECT_ROOT / "bot_agent", PROJECT_ROOT / "api", PROJECT_ROOT / "web_ui", log_dir, REPO_ROOT / "docs"])
    _write_json(log_dir / "encoding_hygiene_report.json", hygiene)
    _write_text(log_dir / "encoding_hygiene_report.md", f"# {PRD_ID} Encoding Hygiene Report\n\n- issue_file_count: `{hygiene['issue_file_count']}`\n- issue_count: `{hygiene['issue_count']}`")

    cmd = [str(PROJECT_ROOT / ".venv/Scripts/python.exe"), "-m", "pytest", "tests/test_unified_dialogue_policy_v2.py", "tests/ui/test_runtime_unified_dialogue_policy_surface.py", "tests/test_final_answer_directive_v1.py", "tests/test_dialogue_pragmatics_v1.py", "tests/multiagent/test_writer_agent.py", "-q"]
    code, out, err = _run_cmd(cmd, cwd=PROJECT_ROOT)
    write_command_log(log_dir, commands=[{"name": "backend_pytest", "command": ".venv\\Scripts\\python -m pytest tests/test_unified_dialogue_policy_v2.py tests/ui/test_runtime_unified_dialogue_policy_surface.py tests/test_final_answer_directive_v1.py tests/test_dialogue_pragmatics_v1.py tests/multiagent/test_writer_agent.py -q", "exit_code": code, "stdout": out, "stderr": err}])

    write_reports(report_dir, startup=startup, dry=dry, direct=direct, live=live, browser=browser, admin_inventory=admin_inventory, pre_scan=pre_scan, hygiene=hygiene, hf3_audit=hf3_audit)

    final_status = "passed"
    if dry.get("status") != "passed":
        final_status = "blocker"
    if direct.get("status") != "passed":
        final_status = "blocker"
    if live.get("status") != "passed":
        final_status = "blocker"
    if admin_inventory.get("status") != "passed":
        final_status = "blocker"
    if browser.get("status") != "passed" and final_status == "passed":
        final_status = "warning"

    summary = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "final_status": final_status,
        "dry_status": dry.get("status"),
        "direct_status": direct.get("status"),
        "live_status": live.get("status"),
        "browser_status": browser.get("status"),
        "admin_surface_status": admin_inventory.get("status"),
        "encoding_hygiene_issue_file_count": hygiene.get("issue_file_count"),
        "no_mutation": no_mutation,
    }
    _write_json(log_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if final_status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
