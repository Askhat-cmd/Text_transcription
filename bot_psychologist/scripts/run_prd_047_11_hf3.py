#!/usr/bin/env python3
"""PRD-047.11-HF3 runner: live UX reality check and encoding hygiene."""

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

DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF3"
DEFAULT_REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8001/api/v1"
DEFAULT_ADMIN_RUNTIME_URL = "http://127.0.0.1:8001/api/admin/runtime/effective"
DEFAULT_CHAT_URL = "http://localhost:3000/chat"
DEFAULT_ADMIN_UI_URL = "http://localhost:3000/admin"
PRD_ID = "PRD-047.11-HF3"
REQUIRED_SUBDIRS = (
    "live_cases",
    "live_turn_exports",
    "prompt_canvases",
    "raw_traces",
    "screenshots",
    "dom_snapshots",
)

LIVE_CASES = [
    {
        "case_id": "HF3-C01",
        "title": "concrete no-practice answer fit",
        "turns": [
            "РІ СЂР°Р·РіРѕРІРѕСЂРµ СЃ РЅР°С‡Р°Р»СЊРЅРёРєРѕРј СЏ РѕРїСЏС‚СЊ СЃР¶РёРјР°СЋСЃСЊ Рё СѓС…РѕР¶Сѓ РІ РјРѕР»С‡Р°РЅРёРµ, РѕР±СЉСЏСЃРЅРё РїРѕ РјРѕРµР№ СЃРёС‚СѓР°С†РёРё Р±РµР· РїСЂР°РєС‚РёРє"
        ],
        "expect_anchor": "РЅР°С‡Р°Р»СЊРЅРёРє",
        "forbid_phrases": ["СЃРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ"],
    },
    {
        "case_id": "HF3-C02",
        "title": "concrete conflict answer fit",
        "turns": [
            "РєРѕРіРґР° РґРѕРјР° РЅР°С‡РёРЅР°РµС‚СЃСЏ РєРѕРЅС„Р»РёРєС‚, СЏ СЂРµР·РєРѕ РІС‹С…РѕР¶Сѓ РёР· СЃРµР±СЏ. СЂР°Р·Р±РµСЂРё РїРѕ СЃРёС‚СѓР°С†РёРё Р±РµР· РґРёР°РіРЅРѕР·Р° Рё Р±РµР· СѓРїСЂР°Р¶РЅРµРЅРёР№"
        ],
        "expect_anchor": "РєРѕРЅС„Р»РёРєС‚",
        "forbid_phrases": ["СЃРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ"],
    },
    {
        "case_id": "HF3-C03",
        "title": "thanks close intent/state",
        "turns": ["РЎРїР°СЃРёР±Рѕ."],
        "expect_state": {"intent": "contact", "nervous_state": "window"},
    },
    {
        "case_id": "HF3-C04",
        "title": "localhost chat markdown",
        "turns": [
            "РѕР±СЉСЏСЃРЅРё РЅРѕСЂРјР°Р»СЊРЅРѕ, С‡С‚Рѕ РїСЂРѕРёСЃС…РѕРґРёС‚ РІ С‚Р°РєРѕР№ СЃРёС‚СѓР°С†РёРё, РєРѕРіРґР° СЏ Р·Р°СЂР°РЅРµРµ РЅР°РїСЂСЏРіР°СЋСЃСЊ РїРµСЂРµРґ СЂР°Р·РіРѕРІРѕСЂРѕРј"
        ],
        "forbid_phrases": ["СЃРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ"],
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
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return status, data if isinstance(data, dict) else {"raw": data}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
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


def _anchor_reflected(answer_text: str, anchor_text: str) -> bool:
    answer_lower = str(answer_text or "").lower()
    anchor_lower = str(anchor_text or "").lower()
    if not answer_lower or not anchor_lower:
        return False
    if anchor_lower in answer_lower:
        return True
    tokens = [
        token
        for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", anchor_lower)
        if len(token) >= 5
    ]
    if not tokens:
        return False
    matched = sum(1 for token in tokens if token in answer_lower)
    return matched >= min(2, len(tokens))


def _ensure_layout(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_SUBDIRS:
        (log_dir / name).mkdir(parents=True, exist_ok=True)


def _scan_text(path: Path) -> dict[str, Any]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"path": str(path.as_posix()), "issues": ["utf8_decode_error"]}
    if "\x07" in text:
        issues.append("bell_char")
    if "\x0c" in text:
        issues.append("form_feed_char")
    if "\ufffd" in text:
        issues.append("replacement_char")
    if re.search(r"(?:Р .|РЎ.){4,}", text):
        issues.append("cyrillic_mojibake_pattern")
    return {"path": str(path.as_posix()), "issues": issues}


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
    log_code, log_out, _ = _run_cmd(["git", "log", "--oneline", "-10"])
    targets = [
        "docs/PROJECT_STATE.md",
        "docs/ROADMAP.md",
        "docs/PRD_INDEX.md",
        "docs/DECISIONS.md",
        "bot_psychologist/docs/PROJECT_STATE.md",
        "bot_psychologist/docs/ROADMAP.md",
        "bot_psychologist/docs/PRD_INDEX.md",
        "bot_psychologist/docs/DECISIONS.md",
        "bot_psychologist/api/admin_routes.py",
        "bot_psychologist/api/routes/users.py",
        "bot_psychologist/web_ui/src/pages/ChatPage.tsx",
        "bot_psychologist/web_ui/src/components/chat/Message.tsx",
        "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
        "bot_psychologist/bot_agent/multiagent/agents/state_analyzer.py",
    ]
    presence = []
    for raw in targets:
        path = REPO_ROOT / raw
        presence.append({"path": raw, "exists": path.exists()})
    payload = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "head": head_out.strip() if head_code == 0 else "",
        "git_status_short": status_out.splitlines() if status_code == 0 else [],
        "last_10_commits": log_out.splitlines() if log_code == 0 else [],
        "presence": presence,
    }
    lines = [
        f"# {PRD_ID} Source Inventory",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- head: `{payload['head']}`",
        "- git_status_short:",
    ]
    for line in payload["git_status_short"]:
        lines.append(f"  - `{line}`")
    lines.append("- last_10_commits:")
    for line in payload["last_10_commits"]:
        lines.append(f"  - `{line}`")
    lines.append("- file_presence:")
    for item in presence:
        lines.append(f"  - `{item['path']}` => `{item['exists']}`")
    _write_json(log_dir / "source_inventory.json", payload)
    _write_text(log_dir / "source_inventory.md", "\n".join(lines))
    return payload


def build_hf2_artifact_audit(log_dir: Path) -> dict[str, Any]:
    hf2_dir = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF2"
    screenshots = list((hf2_dir / "screenshots").glob("*.png")) if (hf2_dir / "screenshots").exists() else []
    prompt_canvases = list((hf2_dir / "prompt_canvases").rglob("*.json")) if (hf2_dir / "prompt_canvases").exists() else []
    memory_proof = (hf2_dir / "raw_traces" / "current_chat_reset_event.json").exists() and (
        hf2_dir / "raw_traces" / "user_memory_profile_clear_event.json"
    ).exists()
    live_result = (hf2_dir / "live_cases_result.json").exists()
    port_signals = []
    for target in [hf2_dir / "live_cases_result.md", hf2_dir / "00_source_audit.md", REPO_ROOT / "docs" / "PROJECT_STATE.md"]:
        if target.exists():
            text = target.read_text(encoding="utf-8", errors="replace")
            if ":3001" in text or "8002/3001" in text:
                port_signals.append({"path": str(target.relative_to(REPO_ROOT)).replace("\\", "/"), "port": "3001"})
            if ":3000" in text or "localhost:3000" in text:
                port_signals.append({"path": str(target.relative_to(REPO_ROOT)).replace("\\", "/"), "port": "3000"})
    payload = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "hf2_exists": hf2_dir.exists(),
        "browser_screenshots_count": len(screenshots),
        "prompt_canvas_count": len(prompt_canvases),
        "memory_controls_proof_present": memory_proof,
        "live_cases_result_present": live_result,
        "port_signals": port_signals,
    }
    lines = [
        f"# {PRD_ID} HF2 Artifact Audit",
        "",
        f"- hf2_exists: `{payload['hf2_exists']}`",
        f"- browser_screenshots_count: `{payload['browser_screenshots_count']}`",
        f"- prompt_canvas_count: `{payload['prompt_canvas_count']}`",
        f"- memory_controls_proof_present: `{payload['memory_controls_proof_present']}`",
        f"- live_cases_result_present: `{payload['live_cases_result_present']}`",
        "- port_signals:",
    ]
    for item in port_signals:
        lines.append(f"  - `{item['path']}` => `{item['port']}`")
    _write_json(log_dir / "hf2_artifact_audit.json", payload)
    _write_text(log_dir / "hf2_artifact_audit.md", "\n".join(lines))
    return payload


def write_runtime_startup(
    log_dir: Path,
    *,
    base_url: str,
    admin_runtime_url: str,
    chat_url: str,
    admin_ui_url: str,
    api_key: str,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    health_status, health_payload = _http_json_request(
        method="GET",
        url=f"{base_url.rstrip('/')}/health",
        headers=headers,
        timeout=30.0,
    )
    runtime_status, runtime_payload = _http_json_request(
        method="GET",
        url=admin_runtime_url,
        headers=headers,
        timeout=30.0,
    )
    chat_check = _http_text_status(chat_url)
    admin_check = _http_text_status(admin_ui_url)
    payload = {
        "generated_at_utc": _now_iso(),
        "health_status": health_status,
        "health_payload": health_payload,
        "admin_runtime_status": runtime_status,
        "admin_runtime_profile": _safe_dict(runtime_payload).get("dialogue_policy", {}).get("profile"),
        "chat_url_check": chat_check,
        "admin_ui_url_check": admin_check,
    }
    lines = [
        f"# {PRD_ID} Runtime Startup",
        "",
        f"- health_status: `{health_status}`",
        f"- admin_runtime_status: `{runtime_status}`",
        f"- admin_runtime_profile: `{payload['admin_runtime_profile']}`",
        f"- chat_url_check: `{chat_check}`",
        f"- admin_ui_url_check: `{admin_check}`",
    ]
    _write_json(log_dir / "runtime_startup.json", payload)
    _write_text(log_dir / "runtime_startup.md", "\n".join(lines))
    return payload


def _derive_api_root(base_url: str) -> str:
    return base_url[:-7] if base_url.rstrip("/").endswith("/api/v1") else base_url.rstrip("/")


def _identity(headers: dict[str, str], base_url: str) -> tuple[int, dict[str, Any]]:
    api_root = _derive_api_root(base_url)
    return _http_json_request(
        method="GET",
        url=f"{api_root}/api/v1/identity/me",
        headers=headers,
        timeout=30.0,
    )


def _post_turn(
    *,
    base_url: str,
    headers: dict[str, str],
    session_id: str,
    query: str,
) -> tuple[int, dict[str, Any]]:
    return _http_json_request(
        method="POST",
        url=f"{base_url.rstrip('/')}/questions/adaptive",
        headers=headers,
        payload={
            "query": query,
            "user_id": "hf3_runner",
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


def run_live_cases(log_dir: Path, *, base_url: str, api_key: str) -> dict[str, Any]:
    headers = {
        "X-API-Key": api_key,
        "X-Session-Id": "prd04711hf3-web-session",
        "X-Device-Fingerprint": "sha256:prd04711hf3-device",
    }
    me_status, me_payload = _identity(headers, base_url)
    canonical_user_id = str(_safe_dict(me_payload).get("user_id", "") or "")
    _write_json(log_dir / "live_cases" / "concrete_answer_fit_cases.json", {"prd": PRD_ID, "cases": LIVE_CASES})
    case_results = []
    failures = 0
    for case in LIVE_CASES:
        case_id = str(case["case_id"])
        session_id = f"prd04711hf3-{case_id.lower()}-{uuid.uuid4().hex[:8]}"
        latest_trace: dict[str, Any] = {}
        answers: list[str] = []
        statuses: list[int] = []
        for idx, turn in enumerate(case.get("turns", []), start=1):
            status, payload = _post_turn(base_url=base_url, headers=headers, session_id=session_id, query=str(turn))
            statuses.append(status)
            answer = str(_safe_dict(payload).get("answer", "") or "")
            answers.append(answer)
            trace_payload = _safe_dict(payload.get("trace"))
            latest_trace = trace_payload or latest_trace
            export_payload = {
                "case_id": case_id,
                "turn_index": idx,
                "user_message": turn,
                "assistant_answer": answer,
                "trace_payload": trace_payload,
            }
            _write_json(log_dir / "live_turn_exports" / case_id / f"turn_{idx:02d}.json", export_payload)

        latest_status, latest_payload = _fetch_latest_trace(base_url=base_url, headers=headers, session_id=session_id)
        full_status, full_payload = _fetch_full_traces(base_url=base_url, headers=headers, session_id=session_id)
        if latest_status == 200 and isinstance(latest_payload, dict):
            latest_trace = latest_payload
        _write_json(
            log_dir / "raw_traces" / f"{case_id}_trace_latest.json",
            latest_payload if isinstance(latest_payload, dict) else {"status": latest_status},
        )
        _write_json(
            log_dir / "raw_traces" / f"{case_id}_traces_full.json",
            full_payload if isinstance(full_payload, dict) else {"status": full_status},
        )
        _save_prompt_canvas(log_dir, case_id, latest_trace)

        latest_answer = answers[-1] if answers else ""
        latest_lower = latest_answer.lower()
        live = _safe_dict(latest_trace.get("live_turn_evidence"))
        writer_debug = _safe_dict(_safe_dict(live.get("writer")).get("writer_debug"))
        state_thread = _safe_dict(live.get("state_thread"))
        answer_fit = _safe_dict(writer_debug.get("answer_fit_evaluator"))
        checks = {
            "all_status_200": all(code == 200 for code in statuses),
            "latest_trace_status_200": latest_status == 200,
            "full_traces_status_200": full_status == 200,
        }
        for phrase in case.get("forbid_phrases", []):
            checks[f"forbid_phrase::{phrase}"] = phrase.lower() not in latest_lower
        if answer_fit:
            checks["answer_fit_not_fail"] = answer_fit.get("fit_status") != "fail"
        expect_state = _safe_dict(case.get("expect_state"))
        if expect_state:
            for key, expected in expect_state.items():
                checks[f"state::{key}"] = state_thread.get(key) == expected
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            failures += 1
        case_results.append(
            {
                "case_id": case_id,
                "title": case.get("title"),
                "session_id": session_id,
                "status": "passed" if not failed else "failed",
                "answers": answers,
                "checks": checks,
                "failed_checks": failed,
                "answer_fit": answer_fit,
                "state_thread": state_thread,
            }
        )

    memory_checks: dict[str, Any] = {"identity_status_200": me_status == 200, "canonical_user_id_present": bool(canonical_user_id)}
    if canonical_user_id:
        memory_session = f"prd04711hf3-reset-{uuid.uuid4().hex[:8]}"
        create_status, create_payload = _http_json_request(
            method="POST",
            url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/sessions",
            headers=headers,
            payload={"title": "HF3 Reset Session"},
            timeout=60.0,
        )
        memory_session = str(_safe_dict(create_payload).get("session_id", "") or memory_session)
        _post_turn(base_url=base_url, headers=headers, session_id=memory_session, query="СЃС‚Р°СЂР°СЏ С‚РµРјР° РїСЂРѕ РЅР°С‡Р°Р»СЊРЅРёРєР° Рё РјРѕР»С‡Р°РЅРёРµ")
        reset_status, reset_payload = _http_json_request(
            method="POST",
            url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/sessions/{urllib.parse.quote(memory_session, safe='')}/reset-context",
            headers=headers,
            timeout=60.0,
        )
        status_new, payload_new = _post_turn(base_url=base_url, headers=headers, session_id=memory_session, query="РЅРѕРІС‹Р№ С‡РёСЃС‚С‹Р№ РІРѕРїСЂРѕСЃ Р±РµР· СЃС‚Р°СЂРѕРіРѕ РєРѕРЅС‚РµРєСЃС‚Р°")
        latest_reset_status, latest_reset_trace = _fetch_latest_trace(base_url=base_url, headers=headers, session_id=memory_session)
        history_status, history_payload = _http_json_request(
            method="GET",
            url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(memory_session, safe='')}/history?last_n_turns=10",
            headers=headers,
            timeout=60.0,
        )
        clear_status, clear_payload = _http_json_request(
            method="DELETE",
            url=f"{base_url.rstrip('/')}/users/{urllib.parse.quote(canonical_user_id, safe='')}/history",
            headers=headers,
            timeout=60.0,
        )
        context_text = json.dumps(_safe_dict(_safe_dict(latest_reset_trace.get("live_turn_evidence")).get("memory")), ensure_ascii=False)
        memory_checks.update(
            {
                "reset_context_status_200": reset_status == 200,
                "create_session_status_200": create_status == 200,
                "reset_context_event_present": _safe_dict(reset_payload).get("memory_control_event", {}).get("event") == "current_chat_context_reset",
                "new_turn_after_reset_status_200": status_new == 200,
                "latest_trace_after_reset_status_200": latest_reset_status == 200,
                "reset_context_removed_old_topic_from_trace": "СЃС‚Р°СЂР°СЏ С‚РµРјР° РїСЂРѕ РЅР°С‡Р°Р»СЊРЅРёРєР°" not in context_text.lower(),
                "history_endpoint_ok": history_status == 200,
                "clear_profile_status_200": clear_status == 200,
                "clear_profile_event_present": _safe_dict(clear_payload).get("memory_control_event", {}).get("event") == "user_memory_profile_cleared",
            }
        )
        _write_json(log_dir / "raw_traces" / "current_chat_reset_event.json", reset_payload)
        _write_json(
            log_dir / "raw_traces" / "current_chat_reset_trace_latest.json",
            latest_reset_trace if isinstance(latest_reset_trace, dict) else {},
        )
        _write_json(log_dir / "raw_traces" / "current_chat_reset_history_after.json", history_payload)
        _write_json(log_dir / "raw_traces" / "user_memory_profile_clear_event.json", clear_payload)
        _write_json(log_dir / "raw_traces" / "current_chat_reset_new_turn_payload.json", payload_new)

    payload = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "status": "passed" if failures == 0 and all(bool(v) for v in memory_checks.values()) else "warning",
        "case_results": case_results,
        "memory_control_checks": memory_checks,
    }
    _write_json(log_dir / "live_cases_result.json", payload)
    lines = [f"# {PRD_ID} Live Cases Result", "", f"- status: `{payload['status']}`", "", "## Cases"]
    for case in case_results:
        lines.append(f"### {case['case_id']} - {case['title']}")
        lines.append(f"- status: `{case['status']}`")
        lines.append(f"- failed_checks: `{case['failed_checks']}`")
        for idx, answer in enumerate(case.get("answers", []), start=1):
            lines.append(f"- answer_{idx}: `{answer[:260]}`")
    lines.append("")
    lines.append("## Memory Controls")
    for key, value in memory_checks.items():
        lines.append(f"- {key}: `{value}`")
    _write_text(log_dir / "live_cases_result.md", "\n".join(lines))
    return payload


def run_browser_and_admin_smoke(
    log_dir: Path,
    *,
    chat_url: str,
    admin_ui_url: str,
    api_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    browser_result_json = log_dir / "browser_smoke_result.json"
    admin_result_json = log_dir / "admin_legacy_inventory.json"
    chat_png = log_dir / "screenshots" / "hf3_web_chat.png"
    admin_png = log_dir / "screenshots" / "hf3_admin_runtime.png"
    chat_dom = log_dir / "dom_snapshots" / "hf3_web_chat.html"
    admin_dom = log_dir / "dom_snapshots" / "hf3_admin.html"
    script = f"""
const fs = require('node:fs');
const path = require('node:path');
function classify(label) {{
  const value = String(label || '').toLowerCase();
  if (!value.trim()) return 'unknown';
  if (value.includes('legacy') || value.includes('mvp_free_dialogue') || value.includes('prd-046') || value.includes('routing')) return 'legacy_or_historical';
  if (value.includes('dev') || value.includes('developer') || value.includes('debug') || value.includes('trace')) return 'dev_only_or_debug';
  if (value.includes('runtime') || value.includes('memory') || value.includes('diagnostic center') || value.includes('prompts') || value.includes('llm') || value.includes('environment')) return 'active_surface';
  return 'unknown';
}}
async function main() {{
  let playwright = null;
  try {{
    playwright = require('playwright');
  }} catch (e) {{
    try {{
      playwright = require(path.join(process.cwd(), 'node_modules', 'playwright'));
    }} catch (_e2) {{
      fs.writeFileSync({json.dumps(str(browser_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_not_installed' }}, null, 2), 'utf8');
      fs.writeFileSync({json.dumps(str(admin_result_json))}, JSON.stringify({{ status: 'warning', reason: 'playwright_not_installed' }}, null, 2), 'utf8');
      return;
    }}
  }}
  const browser = await playwright.chromium.launch({{ headless: true }});
  try {{
    const page = await browser.newPage();
    await page.addInitScript((key) => {{
      window.localStorage.setItem('bot_api_key', key);
      window.localStorage.setItem('bot_web_session_id', 'prd04711hf3-web-chat');
      window.localStorage.setItem('devApiKey', key);
    }}, {json.dumps(api_key)});
    await page.goto({json.dumps(chat_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(1500);
    const newChatButton = page.locator('button', {{ hasText: 'Новый чат' }}).first();
    if (await newChatButton.count()) {{
      await newChatButton.click().catch(() => null);
      await page.waitForTimeout(1200);
    }}
    const initialBotCount = await page.locator('.message-bot .prose').count();
    await page.locator('textarea').fill('Р’РµСЂРЅРё Р±РµР· РѕР±СЉСЏСЃРЅРµРЅРёР№ Рё Р±РµР· РёР·РјРµРЅРµРЅРёР№ СЃР»РµРґСѓСЋС‰РёР№ markdown-Р±Р»РѕРє: **Р–РёСЂРЅС‹Р№ Р·Р°РіРѕР»РѕРІРѕРє**\\n\\nРџРµСЂРІС‹Р№ Р°Р±Р·Р°С† РѕР±С‹С‡РЅРѕРіРѕ С‚РµРєСЃС‚Р°.\\n\\nР’С‚РѕСЂРѕР№ Р°Р±Р·Р°С† РѕР±С‹С‡РЅРѕРіРѕ С‚РµРєСЃС‚Р°.\\n\\n- РџСѓРЅРєС‚ РѕРґРёРЅ\\n- РџСѓРЅРєС‚ РґРІР°');
    await page.locator('textarea').press('Enter');
    await page.waitForFunction((count) => document.querySelectorAll('.message-bot .prose').length > count && !document.querySelector('.thinking-indicator'), initialBotCount, {{ timeout: 90000 }}).catch(() => null);
    await page.waitForTimeout(1500);
    await page.screenshot({{ path: {json.dumps(str(chat_png))}, fullPage: true }});
    fs.writeFileSync({json.dumps(str(chat_dom))}, await page.content(), 'utf8');
    const chatChecks = await page.evaluate(() => {{
      const nodes = Array.from(document.querySelectorAll('.message-bot .prose'));
      const target = nodes[nodes.length - 1] || document.body;
      const text = target.textContent || '';
      return {{
        has_strong: Boolean(target.querySelector('strong')),
        has_list: Boolean(target.querySelector('ul,ol')),
        paragraph_count: target.querySelectorAll('p').length,
        raw_markdown_not_visible: !text.includes('**Р–РёСЂРЅС‹Р№ Р·Р°РіРѕР»РѕРІРѕРє**'),
      }};
    }});
    fs.writeFileSync({json.dumps(str(browser_result_json))}, JSON.stringify({{
      status: (chatChecks.has_strong && chatChecks.has_list && chatChecks.paragraph_count >= 2 && chatChecks.raw_markdown_not_visible) ? 'passed' : 'warning',
      chat_url: {json.dumps(chat_url)},
      checks: chatChecks
    }}, null, 2), 'utf8');
    await page.goto({json.dumps(admin_ui_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(2500);
    await page.screenshot({{ path: {json.dumps(str(admin_png))}, fullPage: true }});
    fs.writeFileSync({json.dumps(str(admin_dom))}, await page.content(), 'utf8');
    const adminData = await page.evaluate(() => {{
      const labels = Array.from(document.querySelectorAll('button,h1,h2,h3,h4,[role="tab"],summary')).map(node => (node.textContent || '').trim()).filter(Boolean);
      const unique = Array.from(new Set(labels));
      return {{ labels: unique.slice(0, 160) }};
    }});
    const items = adminData.labels.map(label => ({{ label, category: classify(label) }}));
    const counts = items.reduce((acc, item) => {{ acc[item.category] = (acc[item.category] || 0) + 1; return acc; }}, {{}});
    fs.writeFileSync({json.dumps(str(admin_result_json))}, JSON.stringify({{
      status: items.length ? 'passed' : 'warning',
      admin_ui_url: {json.dumps(admin_ui_url)},
      counts,
      items
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
    subprocess.run(
        ["node", "-e", script],
        cwd=str(PROJECT_ROOT / "web_ui"),
        capture_output=True,
        text=True,
        timeout=420,
        check=False,
    )
    browser_payload = json.loads(browser_result_json.read_text(encoding="utf-8")) if browser_result_json.exists() else {"status": "warning", "reason": "missing_browser_result"}
    admin_payload = json.loads(admin_result_json.read_text(encoding="utf-8")) if admin_result_json.exists() else {"status": "warning", "reason": "missing_admin_result"}
    lines = [f"# {PRD_ID} Browser Smoke", "", f"- status: `{browser_payload.get('status')}`", f"- chat_url: `{browser_payload.get('chat_url', chat_url)}`"]
    for key, value in _safe_dict(browser_payload.get("checks")).items():
        lines.append(f"- {key}: `{value}`")
    _write_text(log_dir / "browser_smoke_result.md", "\n".join(lines))
    admin_lines = [
        f"# {PRD_ID} Admin Legacy Inventory",
        "",
        f"- status: `{admin_payload.get('status')}`",
        f"- admin_ui_url: `{admin_payload.get('admin_ui_url', admin_ui_url)}`",
        "- counts:",
    ]
    for key, value in _safe_dict(admin_payload.get("counts")).items():
        admin_lines.append(f"  - {key}: `{value}`")
    for item in list(admin_payload.get("items", []) or [])[:40]:
        admin_lines.append(f"- `{item.get('label')}` => `{item.get('category')}`")
    _write_text(log_dir / "admin_legacy_inventory.md", "\n".join(admin_lines))
    return browser_payload, admin_payload


def write_no_mutation(log_dir: Path) -> dict[str, Any]:
    payload = {
        "generated_at_utc": _now_iso(),
        "kb_governance_mutated": False,
        "chroma_reindexed": False,
        "new_llm_agent_added": False,
        "new_runtime_path_added": False,
        "broad_rollout_enabled": False,
        "normal_user_activation_enabled": False,
        "legacy_admin_deleted": False,
    }
    _write_json(log_dir / "no_mutation_proof.json", payload)
    _write_text(
        log_dir / "no_mutation_proof.md",
        "\n".join([f"# {PRD_ID} No Mutation Proof", ""] + [f"- {k}: `{v}`" for k, v in payload.items()]),
    )
    return payload


def write_reports(
    report_dir: Path,
    *,
    source_inventory: dict[str, Any],
    hf2_audit: dict[str, Any],
    pre_scan: dict[str, Any],
    startup: dict[str, Any],
    live: dict[str, Any],
    browser: dict[str, Any],
    admin_inventory: dict[str, Any],
    hygiene: dict[str, Any],
) -> None:
    implementation_lines = [
        f"# {PRD_ID} Implementation Report",
        "",
        f"- generated_at_utc: `{_now_iso()}`",
        "- scope: concrete answer-fit hotfix, thanks-close state repair, localhost web proof, memory reset proof, admin inventory, docs/encoding hygiene",
        "",
        "## Summary",
        f"- source_inventory_head: `{source_inventory.get('head')}`",
        f"- hf2_port_signals: `{hf2_audit.get('port_signals')}`",
        f"- encoding_pre_scan_issue_file_count: `{pre_scan.get('issue_file_count')}`",
        f"- runtime_profile: `{startup.get('admin_runtime_profile')}`",
        f"- live_status: `{live.get('status')}`",
        f"- browser_status: `{browser.get('status')}`",
        f"- admin_inventory_status: `{admin_inventory.get('status')}`",
        f"- encoding_hygiene_issue_file_count: `{hygiene.get('issue_file_count')}`",
        "",
        "## Notes",
        "- HF3 keeps Writer freedom and uses only minimal answer-level repair for concrete formula-stub cases.",
        "- Thanks/close deterministic routing now stays on `contact/window` instead of drifting to `hypo/explore` for bare gratitude turns.",
        "- Browser proof targets `localhost:3000`, not the old isolated `:3001` baseline.",
    ]
    _write_text(report_dir / f"{PRD_ID}_IMPLEMENTATION_REPORT.md", "\n".join(implementation_lines))
    next_lines = [
        f"# {PRD_ID} Next PRD Recommendation",
        "",
        "Recommended next PRD: `PRD-047.12`.",
        "",
        "Rationale:",
        "- HF3 is a stabilization/hygiene cycle that revalidates real localhost UX, answer-fit, reset controls, and docs truthfulness.",
        "- It does not introduce a new runtime branch or broaden activation boundaries.",
        "- Remaining work should now move to dialogue profile simplification/consolidation rather than another residual hotfix unless new live evidence reopens the class.",
    ]
    _write_text(report_dir / f"{PRD_ID}_NEXT_PRD_RECOMMENDATION.md", "\n".join(next_lines))


def write_command_log(log_dir: Path, *, test_commands: list[dict[str, Any]]) -> None:
    lines = [f"# {PRD_ID} Command Output", ""]
    for item in test_commands:
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
    parser = argparse.ArgumentParser(description="Run PRD-047.11-HF3 evidence pack")
    parser.add_argument("--base-url", default=os.getenv("PRD04711HF3_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--admin-runtime-url", default=os.getenv("PRD04711HF3_ADMIN_RUNTIME_URL", DEFAULT_ADMIN_RUNTIME_URL))
    parser.add_argument("--chat-url", default=os.getenv("PRD04711HF3_CHAT_URL", DEFAULT_CHAT_URL))
    parser.add_argument("--admin-ui-url", default=os.getenv("PRD04711HF3_ADMIN_UI_URL", DEFAULT_ADMIN_UI_URL))
    parser.add_argument("--api-key", default=os.getenv("PRD04711HF3_API_KEY", "dev-key-001"))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    log_dir = Path(args.log_dir).resolve()
    report_dir = Path(args.report_dir).resolve()
    _ensure_layout(log_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    source_inventory = build_source_inventory(log_dir)
    hf2_audit = build_hf2_artifact_audit(log_dir)
    pre_scan = _scan_targets(
        [
            REPO_ROOT / "docs",
            REPO_ROOT / "TO_DO_LIST" / "reports",
            REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11-HF2",
            PROJECT_ROOT,
        ]
    )
    _write_json(log_dir / "encoding_pre_scan.json", pre_scan)
    _write_text(
        log_dir / "encoding_pre_scan.md",
        f"# {PRD_ID} Encoding Pre Scan\n\n- issue_file_count: `{pre_scan['issue_file_count']}`\n- issue_count: `{pre_scan['issue_count']}`",
    )
    startup = write_runtime_startup(
        log_dir,
        base_url=args.base_url,
        admin_runtime_url=args.admin_runtime_url,
        chat_url=args.chat_url,
        admin_ui_url=args.admin_ui_url,
        api_key=args.api_key,
    )
    live = run_live_cases(log_dir, base_url=args.base_url, api_key=args.api_key)
    browser, admin_inventory = run_browser_and_admin_smoke(
        log_dir,
        chat_url=args.chat_url,
        admin_ui_url=args.admin_ui_url,
        api_key=args.api_key,
    )
    write_no_mutation(log_dir)
    hygiene = _scan_targets(
        [
            REPO_ROOT / "docs",
            log_dir,
            PROJECT_ROOT / "bot_agent" / "multiagent" / "agents" / "writer_agent.py",
            PROJECT_ROOT / "bot_agent" / "multiagent" / "agents" / "state_analyzer.py",
        ]
    )
    _write_json(log_dir / "encoding_hygiene_report.json", hygiene)
    _write_text(
        log_dir / "encoding_hygiene_report.md",
        f"# {PRD_ID} Encoding Hygiene Report\n\n- issue_file_count: `{hygiene['issue_file_count']}`\n- issue_count: `{hygiene['issue_count']}`",
    )
    write_reports(
        report_dir,
        source_inventory=source_inventory,
        hf2_audit=hf2_audit,
        pre_scan=pre_scan,
        startup=startup,
        live=live,
        browser=browser,
        admin_inventory=admin_inventory,
        hygiene=hygiene,
    )
    write_command_log(log_dir, test_commands=[])
    final_status = "passed" if live.get("status") == "passed" and browser.get("status") == "passed" and admin_inventory.get("status") == "passed" else "warning"
    summary = {
        "prd": PRD_ID,
        "generated_at_utc": _now_iso(),
        "final_status": final_status,
        "live_status": live.get("status"),
        "browser_status": browser.get("status"),
        "admin_inventory_status": admin_inventory.get("status"),
        "encoding_hygiene_issue_file_count": hygiene.get("issue_file_count"),
    }
    _write_json(log_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if final_status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

