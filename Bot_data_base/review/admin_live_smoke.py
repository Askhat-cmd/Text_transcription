from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .review_sanitizer import contains_secret_like_value


ENDPOINTS = ["/api/status", "/api/registry", "/api/dashboard", "/api/dashboard/"]
DEFAULT_SOURCE_ID = "123__кузница_духа"
DEFAULT_BLOCKS_TOTAL = 247


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": body, "error": None}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def discover_canonical_launch_command(*, repo_root: Path, admin_base_url: str) -> dict[str, Any]:
    search_paths = [
        repo_root / "Bot_data_base" / "README.md",
        repo_root / "Bot_data_base" / "LAUNCH.md",
    ]
    pattern = "uvicorn api.main:app"
    source_marker = ""

    for path in search_paths:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            if pattern in line:
                source_marker = f"{path.relative_to(repo_root)}:{idx}"
                break
        if source_marker:
            break

    parsed = urlparse(admin_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000

    botdb_dir = repo_root / "Bot_data_base"
    venv_python = botdb_dir / ".venv" / "Scripts" / "python.exe"
    python_exec = str(venv_python) if venv_python.exists() else sys.executable

    command = [
        python_exec,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    return {
        "canonical_launch_command_found": bool(source_marker),
        "canonical_launch_command": command,
        "canonical_launch_command_str": subprocess.list2cmdline(command),
        "launch_command_source": source_marker or "not_found_in_repo_docs",
        "cwd": str(botdb_dir),
    }


def _poll_readiness(
    *,
    admin_base_url: str,
    timeout_sec: int,
    http_get: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    deadline = time.monotonic() + max(1, int(timeout_sec))
    attempts = 0
    last_response: dict[str, Any] = {"ok": False, "status_code": None, "body": None, "error": "not_polled"}
    status_url = f"{admin_base_url.rstrip('/')}/api/status"

    while time.monotonic() < deadline:
        attempts += 1
        response = http_get(status_url)
        last_response = response
        body = response.get("body")
        if bool(response.get("ok")) and int(response.get("status_code") or 0) == 200 and isinstance(body, dict):
            return {
                "readiness_passed": True,
                "readiness_poll_attempts": attempts,
                "last_response": response,
            }
        time.sleep(1.0)

    return {
        "readiness_passed": False,
        "readiness_poll_attempts": attempts,
        "last_response": last_response,
    }


def _extract_focus_blocks(registry_body: Any, expected_source_id: str) -> int:
    rows: list[dict[str, Any]] = []
    if isinstance(registry_body, dict):
        source_rows = registry_body.get("sources")
        if isinstance(source_rows, list):
            rows = [item for item in source_rows if isinstance(item, dict)]
    elif isinstance(registry_body, list):
        rows = [item for item in registry_body if isinstance(item, dict)]
    for row in rows:
        if str(row.get("source_id") or "").strip() == expected_source_id:
            return int(row.get("blocks_count") or 0)
    return 0


def _extract_dashboard_blocks_count(dashboard_body: Any) -> int | None:
    if not isinstance(dashboard_body, dict):
        return None
    blocks = dashboard_body.get("blocks")
    if isinstance(blocks, dict):
        for key in ("production_total", "active_source_blocks", "registry_total"):
            value = blocks.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
    return None


def _extract_dashboard_chroma_count(dashboard_body: Any) -> int | None:
    if not isinstance(dashboard_body, dict):
        return None
    chroma = dashboard_body.get("chroma")
    if isinstance(chroma, dict):
        value = chroma.get("count")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def evaluate_admin_contract(
    *,
    api_checks: dict[str, dict[str, Any]],
    expected_source_id: str,
    expected_blocks_total: int,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    reachable = [endpoint for endpoint in ENDPOINTS if bool((api_checks.get(endpoint) or {}).get("ok"))]
    unreachable = [endpoint for endpoint in ENDPOINTS if endpoint not in reachable]

    if len(unreachable) == len(ENDPOINTS):
        return {
            "admin_runtime_status": "blocked_admin_api_unavailable",
            "admin_consistency_passed": False,
            "issues": ["admin_api_unavailable"],
            "warnings": [],
            "reachable_endpoints": reachable,
            "unreachable_endpoints": unreachable,
            "focus_source_id": expected_source_id,
            "focus_blocks_count": 0,
            "dashboard_blocks_count": None,
            "chroma_count": None,
        }

    non_200 = [
        endpoint
        for endpoint, response in api_checks.items()
        if not bool(response.get("ok")) or int(response.get("status_code") or 0) != 200
    ]
    if non_200:
        return {
            "admin_runtime_status": "blocked_admin_api_unavailable",
            "admin_consistency_passed": False,
            "issues": sorted(["admin_api_partial_or_http_non_200", *[f"endpoint_invalid:{item}" for item in non_200]]),
            "warnings": [],
            "reachable_endpoints": reachable,
            "unreachable_endpoints": unreachable,
            "focus_source_id": expected_source_id,
            "focus_blocks_count": 0,
            "dashboard_blocks_count": None,
            "chroma_count": None,
        }

    status_body = (api_checks.get("/api/status") or {}).get("body")
    registry_body = (api_checks.get("/api/registry") or {}).get("body")
    dashboard_body = (api_checks.get("/api/dashboard") or {}).get("body")
    dashboard_slash_body = (api_checks.get("/api/dashboard/") or {}).get("body")

    if not isinstance(status_body, dict):
        issues.append("status_payload_invalid")
    if not isinstance(registry_body, (dict, list)):
        issues.append("registry_payload_invalid")
    if not isinstance(dashboard_body, dict) or not dashboard_body:
        issues.append("dashboard_payload_invalid")
    if not isinstance(dashboard_slash_body, dict) or not dashboard_slash_body:
        issues.append("dashboard_slash_payload_invalid")

    focus_blocks_count = _extract_focus_blocks(registry_body, expected_source_id)
    if focus_blocks_count != expected_blocks_total:
        issues.append("registry_focus_blocks_mismatch")

    dashboard_blocks_count = _extract_dashboard_blocks_count(dashboard_body)
    if dashboard_blocks_count is None:
        warnings.append("dashboard_blocks_count_field_not_available")
    elif dashboard_blocks_count != expected_blocks_total:
        issues.append("dashboard_blocks_count_mismatch")

    chroma_count = _extract_dashboard_chroma_count(dashboard_body)
    if chroma_count is None:
        warnings.append("dashboard_chroma_count_field_not_available")
    elif chroma_count != expected_blocks_total:
        issues.append("dashboard_chroma_count_mismatch")

    admin_consistency_passed = len(issues) == 0
    return {
        "admin_runtime_status": "passed" if admin_consistency_passed else "failed_schema_validation",
        "admin_consistency_passed": admin_consistency_passed,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "reachable_endpoints": reachable,
        "unreachable_endpoints": unreachable,
        "focus_source_id": expected_source_id,
        "focus_blocks_count": focus_blocks_count,
        "dashboard_blocks_count": dashboard_blocks_count,
        "chroma_count": chroma_count,
    }


def _sanitize_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in raw_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line.strip())
        if not line:
            continue
        if contains_secret_like_value(line):
            lines.append("[redacted_secret_like_line]")
        else:
            lines.append(line[:1200])
    return lines


def _terminate_process(proc: subprocess.Popen[str]) -> str:
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        return "ok"
    except Exception:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            return "failed"
        return "ok"


def run_admin_live_smoke(
    *,
    admin_base_url: str,
    expected_source_id: str = DEFAULT_SOURCE_ID,
    expected_blocks_total: int = DEFAULT_BLOCKS_TOTAL,
    require_admin_api: bool = True,
    try_start_server: bool = False,
    startup_timeout_sec: int = 30,
    repo_root: Path,
    http_get: Callable[[str], dict[str, Any]] | None = None,
    discover_launch: Callable[..., dict[str, Any]] | None = None,
    process_factory: Callable[[list[str], Path, Path], subprocess.Popen[str]] | None = None,
) -> dict[str, Any]:
    fetch = http_get or _http_json
    discover = discover_launch or discover_canonical_launch_command
    botdb_dir = repo_root / "Bot_data_base"

    manifest: dict[str, Any] = {
        "schema_version": "admin_launch_manifest_v1",
        "source_prd": "PRD-046.0.7.2-HF1",
        "generated_at": utc_now_iso(),
        "admin_base_url": admin_base_url,
        "detected_existing_server": False,
        "canonical_launch_command_found": False,
        "canonical_launch_command": "",
        "launch_command_source": "",
        "server_launch_mode": "not_started",
        "server_started_by_hf1": False,
        "startup_timeout_sec": int(startup_timeout_sec),
        "readiness_poll_attempts": 0,
        "readiness_passed": False,
        "shutdown_performed": False,
        "shutdown_status": "not_needed",
    }

    server_process: subprocess.Popen[str] | None = None
    launch_blocker = False
    launch_blocker_reason = ""
    server_log_path = Path(tempfile.gettempdir()) / f"prd_046_0_7_2_hf1_admin_{int(time.time() * 1000)}.log"

    initial_status = fetch(f"{admin_base_url.rstrip('/')}/api/status")
    if bool(initial_status.get("ok")) and int(initial_status.get("status_code") or 0) == 200 and isinstance(initial_status.get("body"), dict):
        manifest["detected_existing_server"] = True
        manifest["server_launch_mode"] = "external_existing"
        manifest["readiness_poll_attempts"] = 1
        manifest["readiness_passed"] = True
    elif try_start_server:
        launch = discover(repo_root=repo_root, admin_base_url=admin_base_url)
        command = launch.get("canonical_launch_command") if isinstance(launch.get("canonical_launch_command"), list) else []
        manifest["canonical_launch_command_found"] = bool(launch.get("canonical_launch_command_found"))
        manifest["canonical_launch_command"] = str(launch.get("canonical_launch_command_str") or "")
        manifest["launch_command_source"] = str(launch.get("launch_command_source") or "")

        if not manifest["canonical_launch_command_found"] or not command:
            launch_blocker = True
            launch_blocker_reason = "canonical_launch_command_not_found"
        else:
            try:
                server_log_path.parent.mkdir(parents=True, exist_ok=True)
                if process_factory is None:
                    log_file = server_log_path.open("w", encoding="utf-8")
                    server_process = subprocess.Popen(  # noqa: S603
                        command,
                        cwd=str(botdb_dir),
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    log_file.close()
                else:
                    server_process = process_factory(command, botdb_dir, server_log_path)
                manifest["server_launch_mode"] = "hf1_subprocess"
                manifest["server_started_by_hf1"] = True
                readiness = _poll_readiness(
                    admin_base_url=admin_base_url,
                    timeout_sec=startup_timeout_sec,
                    http_get=fetch,
                )
                manifest["readiness_poll_attempts"] = int(readiness.get("readiness_poll_attempts") or 0)
                manifest["readiness_passed"] = bool(readiness.get("readiness_passed"))
                if not manifest["readiness_passed"]:
                    launch_blocker = True
                    launch_blocker_reason = "admin_startup_timeout_or_readiness_failed"
            except Exception as exc:
                launch_blocker = True
                launch_blocker_reason = f"admin_subprocess_start_failed:{exc}"
    else:
        manifest["server_launch_mode"] = "not_started"

    checks: dict[str, dict[str, Any]] = {}
    for endpoint in ENDPOINTS:
        checks[endpoint] = fetch(f"{admin_base_url.rstrip('/')}{endpoint}")

    evaluated = evaluate_admin_contract(
        api_checks=checks,
        expected_source_id=expected_source_id,
        expected_blocks_total=expected_blocks_total,
    )

    if launch_blocker:
        admin_runtime_status = "blocked_admin_launch_failed"
        admin_consistency_passed = False
        issues = sorted(set([launch_blocker_reason, *evaluated.get("issues", [])]))
    else:
        admin_runtime_status = str(evaluated.get("admin_runtime_status") or "blocked_admin_api_unavailable")
        admin_consistency_passed = bool(evaluated.get("admin_consistency_passed"))
        issues = list(evaluated.get("issues") or [])

    if not require_admin_api and admin_runtime_status == "blocked_admin_api_unavailable":
        issues = sorted(set(list(issues) + ["admin_api_unavailable_non_strict_mode"]))

    if manifest.get("server_started_by_hf1") and server_process is not None:
        manifest["shutdown_performed"] = True
        manifest["shutdown_status"] = _terminate_process(server_process)

    server_logs = ""
    if server_log_path.exists():
        try:
            server_logs = server_log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            server_logs = ""
        try:
            server_log_path.unlink(missing_ok=True)
        except Exception:
            pass
    sanitized_lines = _sanitize_lines(server_logs)

    smoke = {
        "schema_version": "admin_live_smoke_v1",
        "source_prd": "PRD-046.0.7.2-HF1",
        "generated_at": utc_now_iso(),
        "admin_base_url": admin_base_url,
        "require_admin_api": require_admin_api,
        "try_start_server": try_start_server,
        "startup_timeout_sec": int(startup_timeout_sec),
        "server_launch_mode": manifest.get("server_launch_mode"),
        "server_started_by_hf1": bool(manifest.get("server_started_by_hf1")),
        "detected_existing_server": bool(manifest.get("detected_existing_server")),
        "readiness_poll_attempts": int(manifest.get("readiness_poll_attempts") or 0),
        "readiness_passed": bool(manifest.get("readiness_passed")),
        "api_checks": checks,
        "reachable_endpoints": list(evaluated.get("reachable_endpoints") or []),
        "unreachable_endpoints": list(evaluated.get("unreachable_endpoints") or []),
        "focus_source_id": expected_source_id,
        "focus_blocks_count": evaluated.get("focus_blocks_count"),
        "dashboard_blocks_count": evaluated.get("dashboard_blocks_count"),
        "chroma_count": evaluated.get("chroma_count"),
        "admin_runtime_status": admin_runtime_status,
        "admin_consistency_passed": admin_consistency_passed,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(evaluated.get("warnings") or [])),
    }

    return {
        "manifest": manifest,
        "smoke": smoke,
        "sanitized_server_log_lines": sanitized_lines,
    }
