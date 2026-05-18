from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _http_json(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            body: Any
            try:
                body = json.loads(raw) if raw else None
            except Exception:
                body = raw
            return {"ok": True, "status_code": int(resp.status), "body": body, "error": None}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        try:
            body = json.loads(raw) if raw else raw
        except Exception:
            body = raw
        return {"ok": False, "status_code": int(exc.code), "body": body, "error": f"HTTPError:{exc}"}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return [row for row in payload.get("sources") if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _find_free_port(start_port: int = 8013) -> int:
    port = int(start_port)
    while port < 9000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("no_free_port_for_hf2_acceptance")


def _resolve_python_executable(repo_root: str) -> str:
    repo = Path(repo_root).resolve()
    venv_python = repo / "Bot_data_base" / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _wait_http_ok(url: str, timeout_sec: float = 30.0) -> bool:
    end_at = time.time() + timeout_sec
    while time.time() < end_at:
        probe = _http_json(url, timeout=3.0)
        if bool(probe.get("ok")) and _to_int(probe.get("status_code")) == 200:
            return True
        time.sleep(0.5)
    return False


def _collect_acceptance(*, admin_base_url: str, expected_source_id: str, expected_blocks: int) -> dict[str, Any]:
    base = admin_base_url.rstrip("/")
    checks = {
        "dashboard_page": _http_json(f"{base}/"),
        "registry_page": _http_json(f"{base}/registry"),
        "dashboard_api": _http_json(f"{base}/api/dashboard"),
        "registry_api": _http_json(f"{base}/api/registry/"),
        "registry_stats_api": _http_json(f"{base}/api/registry/stats"),
    }

    dashboard_body = checks["dashboard_api"].get("body") if isinstance(checks["dashboard_api"], dict) else {}
    chroma_block = dashboard_body.get("chroma") if isinstance(dashboard_body, dict) and isinstance(dashboard_body.get("chroma"), dict) else {}
    dashboard_chroma_status = _normalize(chroma_block.get("status")).lower() or "unknown"
    dashboard_chroma_count = _to_int(chroma_block.get("count"))

    stats_body = checks["registry_stats_api"].get("body") if isinstance(checks["registry_stats_api"], dict) else {}
    registry_stats_chroma_status = _normalize(stats_body.get("chroma_status")).lower() if isinstance(stats_body, dict) else ""
    registry_stats_chroma_total = _to_int(stats_body.get("chroma_total")) if isinstance(stats_body, dict) else 0

    rows = _extract_rows(checks["registry_api"].get("body"))
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    focus_row = focus_rows[0] if focus_rows else {}
    focus_source_visible = bool(focus_rows)
    focus_source_blocks = _to_int(focus_row.get("blocks_count")) if focus_rows else 0
    delete_policy = focus_row.get("delete_policy") if isinstance(focus_row.get("delete_policy"), dict) else {}
    focus_source_protected = _normalize(delete_policy.get("state")) == "protected"

    payload = {
        "schema_version": "admin_browser_acceptance_hf2_v1",
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "expected_source_id": expected_source_id,
        "expected_blocks": expected_blocks,
        "checks": checks,
        "dashboard_page_http_200": bool(checks["dashboard_page"].get("ok")) and _to_int(checks["dashboard_page"].get("status_code")) == 200,
        "registry_page_http_200": bool(checks["registry_page"].get("ok")) and _to_int(checks["registry_page"].get("status_code")) == 200,
        "dashboard_api_http_200": bool(checks["dashboard_api"].get("ok")) and _to_int(checks["dashboard_api"].get("status_code")) == 200,
        "registry_api_http_200": bool(checks["registry_api"].get("ok")) and _to_int(checks["registry_api"].get("status_code")) == 200,
        "registry_stats_http_200": bool(checks["registry_stats_api"].get("ok")) and _to_int(checks["registry_stats_api"].get("status_code")) == 200,
        "dashboard_chroma_status": dashboard_chroma_status,
        "dashboard_chroma_count": dashboard_chroma_count,
        "registry_stats_chroma_status": registry_stats_chroma_status,
        "registry_stats_chroma_total": registry_stats_chroma_total,
        "focus_source_visible": focus_source_visible,
        "focus_source_blocks": focus_source_blocks,
        "focus_source_protected": focus_source_protected,
        "registry_global_error_http_500": _to_int(checks["registry_stats_api"].get("status_code")) >= 500,
        "dashboard_chroma_unavailable": dashboard_chroma_status == "unavailable",
        "issues": [],
        "admin_browser_acceptance_passed": False,
    }

    issues: list[str] = []
    required_true = [
        "dashboard_page_http_200",
        "registry_page_http_200",
        "dashboard_api_http_200",
        "registry_api_http_200",
        "registry_stats_http_200",
        "focus_source_visible",
        "focus_source_protected",
    ]
    for key in required_true:
        if not bool(payload.get(key)):
            issues.append(f"{key}_failed")
    if payload["dashboard_chroma_status"] != "ok":
        issues.append("dashboard_chroma_status_not_ok")
    if payload["dashboard_chroma_count"] != expected_blocks:
        issues.append("dashboard_chroma_count_mismatch")
    if payload["registry_stats_chroma_status"] != "ok":
        issues.append("registry_stats_chroma_status_not_ok")
    if payload["registry_stats_chroma_total"] != expected_blocks:
        issues.append("registry_stats_chroma_total_mismatch")
    if payload["focus_source_blocks"] != expected_blocks:
        issues.append("focus_source_blocks_mismatch")
    if payload["registry_global_error_http_500"]:
        issues.append("registry_stats_http_500")
    if payload["dashboard_chroma_unavailable"]:
        issues.append("dashboard_chroma_unavailable")

    payload["issues"] = sorted(set(issues))
    payload["admin_browser_acceptance_passed"] = len(payload["issues"]) == 0
    return payload


def run_acceptance(
    *,
    repo_root: str,
    admin_base_url: str,
    expected_source_id: str,
    expected_blocks: int,
) -> dict[str, Any]:
    payload = _collect_acceptance(
        admin_base_url=admin_base_url,
        expected_source_id=expected_source_id,
        expected_blocks=expected_blocks,
    )
    payload["primary_base_url"] = admin_base_url
    payload["effective_base_url"] = admin_base_url
    payload["runtime_fallback_used"] = False
    payload["fallback_runtime_port"] = None

    if bool(payload.get("admin_browser_acceptance_passed")):
        return payload

    botdb_dir = (Path(repo_root).resolve() / "Bot_data_base").resolve()
    if not botdb_dir.exists():
        payload["runtime_fallback_error"] = "botdb_dir_not_found"
        return payload

    port = _find_free_port(8013)
    python_executable = _resolve_python_executable(repo_root)
    process = subprocess.Popen(  # noqa: S603
        [python_executable, "-m", "uvicorn", "api.main:app", "--port", str(port)],
        cwd=str(botdb_dir),
        env={**os.environ, "BOT_DB_DISABLE_EMBEDDINGS": "1"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_http_ok(f"{base}/api/status/")
        if not ready:
            payload["runtime_fallback_error"] = "fallback_runtime_not_ready"
            return payload
        fallback_payload = {}
        for _ in range(3):
            time.sleep(1.0)
            fallback_payload = _collect_acceptance(
                admin_base_url=base,
                expected_source_id=expected_source_id,
                expected_blocks=expected_blocks,
            )
            dash_ok = bool(fallback_payload.get("dashboard_api_http_200"))
            registry_ok = bool(fallback_payload.get("registry_api_http_200"))
            stats_ok = bool(fallback_payload.get("registry_stats_http_200"))
            if dash_ok and registry_ok and stats_ok:
                break
        fallback_payload["primary_base_url"] = admin_base_url
        fallback_payload["effective_base_url"] = base
        fallback_payload["runtime_fallback_used"] = True
        fallback_payload["fallback_runtime_port"] = port
        return fallback_payload
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 admin browser acceptance gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = run_acceptance(
        repo_root=str(args.repo_root),
        admin_base_url=str(args.admin_base_url),
        expected_source_id=str(args.expected_source_id),
        expected_blocks=int(args.expected_blocks),
    )
    out_path = Path(args.output_dir) / "admin_browser_acceptance.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))

    if args.strict and not bool(payload.get("admin_browser_acceptance_passed")):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
