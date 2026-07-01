from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.36-HF4"
NODE_SCRIPT = BOT_ROOT / "tools" / "prd_047_36_hf4_browser_check.mjs"
BACKEND_BASE_URL = "http://127.0.0.1:8001"
FRONTEND_BASE_URL = "http://localhost:3000"
API_KEY = "dev-key-001"
DEV_HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json; charset=utf-8",
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    response = httpx.request(method, url, headers=headers, json=payload, timeout=timeout)
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text}
    return response.status_code, body if isinstance(body, dict) else {"raw": body}


def _wait_for_backend_health(timeout_seconds: float = 120.0) -> dict[str, Any]:
    started_at = time.time()
    last_payload: dict[str, Any] = {}
    while time.time() - started_at < timeout_seconds:
        try:
            status, payload = _http_json(
                method="GET",
                url=f"{BACKEND_BASE_URL}/api/v1/health",
                headers={"X-API-Key": API_KEY},
                timeout=15.0,
            )
            last_payload = payload
            if status == 200 and payload.get("status") == "healthy":
                return {"status_code": status, "payload": payload}
        except Exception as exc:
            last_payload = {"error": str(exc)}
        time.sleep(2.0)
    raise RuntimeError(f"Backend health did not recover: {last_payload}")


def _restart_backend() -> dict[str, Any]:
    find_pid = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=20,
    )
    pid_text = (find_pid.stdout or "").strip()
    old_pid = int(pid_text) if pid_text.isdigit() else None
    if old_pid is not None:
        subprocess.run(["taskkill", "/PID", str(old_pid), "/F"], cwd=str(REPO_ROOT), timeout=20, check=False)
        time.sleep(3.0)

    start_command = (
        "$env:APP_ENV='local'; "
        "$env:DEBUG_TRACE_ENABLED='true'; "
        "$env:SEMANTIC_CARDS_PILOT_ENABLED='true'; "
        "$env:PYTHONUTF8='1'; "
        "Start-Process -FilePath '.venv\\Scripts\\python.exe' "
        "-ArgumentList '-m','uvicorn','api.main:app','--host','0.0.0.0','--port','8001' "
        "-WorkingDirectory '.' -WindowStyle Hidden"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", start_command],
        cwd=str(BOT_ROOT),
        timeout=20,
        check=True,
    )
    health = _wait_for_backend_health()
    return {
        "killed_pid": old_pid,
        "health_after_restart": health,
    }


def _warm_backend(label: str) -> dict[str, Any]:
    session_id = f"hf4_warm_{label}_{uuid4().hex[:8]}"
    status, payload = _http_json(
        method="POST",
        url=f"{BACKEND_BASE_URL}/api/v1/questions/adaptive",
        headers={**DEV_HEADERS, "X-Session-Id": session_id},
        payload={
            "query": "Привет. Это warm-up turn для browser trace smoke.",
            "session_id": session_id,
            "debug": True,
            "include_path": False,
            "include_feedback_prompt": False,
        },
        timeout=240.0,
    )
    return {
        "session_id": session_id,
        "status_code": status,
        "answer_preview": str(payload.get("answer", ""))[:200],
    }


def _run_browser_phase(
    *,
    mode: str,
    user_id: str,
    web_session_id: str,
    old_session_id: str | None = None,
) -> dict[str, Any]:
    config_path = OUT_DIR / f"browser_{mode}_config.json"
    result_path = OUT_DIR / f"browser_{mode}_result.json"
    payload = {
        "mode": mode,
        "api_key": API_KEY,
        "backend_base_url": BACKEND_BASE_URL,
        "frontend_base_url": FRONTEND_BASE_URL,
        "user_id": user_id,
        "web_session_id": web_session_id,
        "old_session_id": old_session_id,
        "output_dir": str(OUT_DIR),
        "result_path": str(result_path),
    }
    _write_json(config_path, payload)
    subprocess.run(
        ["node", str(NODE_SCRIPT), str(config_path)],
        cwd=str(BOT_ROOT / "web_ui"),
        timeout=600,
        check=True,
    )
    return json.loads(result_path.read_text(encoding="utf-8"))


def _fetch_history_turns(*, user_scope: str, session_header: str) -> list[int]:
    status, payload = _http_json(
        method="GET",
        url=f"{BACKEND_BASE_URL}/api/v1/users/{user_scope}/history?last_n_turns=100",
        headers={"X-API-Key": API_KEY, "X-Session-Id": session_header},
        timeout=60.0,
    )
    if status != 200:
        return []
    turns = payload.get("turns", []) or []
    numbers: list[int] = []
    for item in turns:
        if isinstance(item, dict):
            try:
                parsed = int(item.get("turn_number"))
            except (TypeError, ValueError):
                continue
            numbers.append(parsed)
    return numbers


def _fetch_trace_result(*, session_id: str, turn_index: int) -> dict[str, Any]:
    status, payload = _http_json(
        method="GET",
        url=f"{BACKEND_BASE_URL}/api/debug/session/{session_id}/multiagent-trace?turn_index={turn_index}",
        headers={"X-API-Key": API_KEY},
        timeout=60.0,
    )
    availability = payload.get("trace_availability") if isinstance(payload.get("trace_availability"), dict) else {}
    return {
        "status_code": status,
        "turn_index": payload.get("turn_index"),
        "detail": payload.get("detail"),
        "availability": availability,
        "available_turn_indices": payload.get("available_turn_indices", []),
    }


def run_smoke() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    user_id = f"hf4_user_{uuid4().hex[:10]}"
    web_session_id = f"hf4_web_{uuid4().hex[:10]}"
    frontend_status = 0
    try:
        frontend_status = httpx.get(FRONTEND_BASE_URL, timeout=15.0).status_code
    except Exception:
        frontend_status = 0

    initial_restart = _restart_backend()
    initial_warmup = _warm_backend("initial")

    pre_restart = _run_browser_phase(
        mode="pre_restart",
        user_id=user_id,
        web_session_id=web_session_id,
    )
    old_session_id = str(pre_restart.get("old_session_id") or "")
    pre_restart_trace_checks = {
        f"turn_{turn}": _fetch_trace_result(session_id=old_session_id, turn_index=turn)
        for turn in range(1, 6)
    }
    pre_restart_history_turns = _fetch_history_turns(user_scope=old_session_id, session_header=web_session_id)

    restart_info = _restart_backend()
    restart_warmup = _warm_backend("post_restart")

    post_restart = _run_browser_phase(
        mode="post_restart",
        user_id=user_id,
        web_session_id=web_session_id,
        old_session_id=old_session_id,
    )
    new_session_id = str(post_restart.get("new_session_id") or "")

    old_session_after_restart = _fetch_trace_result(session_id=old_session_id, turn_index=1)
    new_session_trace_checks = {
        f"turn_{turn}": _fetch_trace_result(session_id=new_session_id, turn_index=turn)
        for turn in range(1, 3)
    }
    new_session_history_turns = _fetch_history_turns(user_scope=new_session_id, session_header=web_session_id)

    return {
        "verdict": "PASS",
        "user_id": user_id,
        "web_session_id": web_session_id,
        "frontend_status": frontend_status,
        "backend_restart_initial": initial_restart,
        "backend_warmup_initial": initial_warmup,
        "pre_restart": {
            "browser": pre_restart,
            "history_turns": pre_restart_history_turns,
            "trace_checks": pre_restart_trace_checks,
        },
        "backend_restart": restart_info,
        "backend_warmup_post_restart": restart_warmup,
        "post_restart": {
            "browser": post_restart,
            "old_session_trace_check": old_session_after_restart,
            "new_session_history_turns": new_session_history_turns,
            "new_session_trace_checks": new_session_trace_checks,
        },
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    result = run_smoke()
    _write_json(OUT_DIR / "live_smoke_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
