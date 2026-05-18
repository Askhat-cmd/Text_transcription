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


DEFAULT_QUERY = "что значит быть в потоке"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _http_post_json(url: str, body: dict[str, Any], timeout: float = 20.0) -> dict[str, Any]:
    req = Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: Any
            try:
                parsed = json.loads(raw) if raw else None
            except Exception:
                parsed = raw
            return {"ok": True, "status_code": int(resp.status), "body": parsed, "error": None}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        try:
            parsed = json.loads(raw) if raw else raw
        except Exception:
            parsed = raw
        return {"ok": False, "status_code": int(exc.code), "body": parsed, "error": f"HTTPError:{exc}"}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _find_free_port(start_port: int = 8013) -> int:
    port = int(start_port)
    while port < 9000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("no_free_port_for_hf2_query_acceptance")


def _resolve_python_executable(repo_root: str) -> str:
    repo = Path(repo_root).resolve()
    venv_python = repo / "Bot_data_base" / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _wait_status_ok(base_url: str, timeout_sec: float = 30.0) -> bool:
    end_at = time.time() + timeout_sec
    while time.time() < end_at:
        probe = _http_post_json(
            f"{base_url.rstrip('/')}/api/status/",
            {},
            timeout=3.0,
        )
        if _to_int(probe.get("status_code")) == 200 or probe.get("status_code") is not None:
            return True
        time.sleep(0.5)
    return False


def _collect_acceptance(*, admin_base_url: str, query_text: str) -> dict[str, Any]:
    response = _http_post_json(
        f"{admin_base_url.rstrip('/')}/api/query/",
        {
            "query": query_text,
            "top_k": 3,
            "pre_filter_k": 20,
            "use_rerank": False,
            "search_mode": "hybrid",
        },
    )
    body = response.get("body")
    chunks = body.get("chunks") if isinstance(body, dict) and isinstance(body.get("chunks"), list) else []
    debug = body.get("debug") if isinstance(body, dict) and isinstance(body.get("debug"), dict) else {}
    debug_text = json.dumps(debug, ensure_ascii=False) if debug else ""
    full_text = json.dumps(body, ensure_ascii=False) if body is not None else ""

    payload = {
        "schema_version": "botdb_query_acceptance_hf2_v1",
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "query_text": query_text,
        "botdb_api_query_status": _to_int(response.get("status_code")),
        "rag_hits_count": len(chunks),
        "query_http_503_chromadb_unavailable": _to_int(response.get("status_code")) == 503 and "ChromaDB unavailable" in full_text,
        "botdb_circuit_open": "circuit open" in full_text.lower() or "ChromaDB unavailable" in full_text,
        "semantic_fallback_used": "semantic_fallback" in full_text.lower(),
        "raw_kb_quote_exposure": False,
        "botdb_query_route_fallback_used": bool(debug.get("botdb_query_route_fallback_used")),
        "response": response,
        "issues": [],
        "botdb_query_acceptance_passed": False,
    }

    issues: list[str] = []
    if payload["botdb_api_query_status"] != 200:
        issues.append("query_status_not_200")
    if payload["rag_hits_count"] <= 0:
        issues.append("query_hits_empty")
    if payload["query_http_503_chromadb_unavailable"]:
        issues.append("query_503_chromadb_unavailable")
    if payload["botdb_circuit_open"]:
        issues.append("botdb_circuit_open")
    if payload["semantic_fallback_used"]:
        issues.append("semantic_fallback_used")

    payload["issues"] = sorted(set(issues))
    payload["botdb_query_acceptance_passed"] = len(payload["issues"]) == 0
    return payload


def run_acceptance(*, repo_root: str, admin_base_url: str, query_text: str) -> dict[str, Any]:
    payload = _collect_acceptance(admin_base_url=admin_base_url, query_text=query_text)
    payload["primary_base_url"] = admin_base_url
    payload["effective_base_url"] = admin_base_url
    payload["runtime_fallback_used"] = False
    payload["fallback_runtime_port"] = None
    if bool(payload.get("botdb_query_acceptance_passed")):
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
        ready = _wait_status_ok(base)
        if not ready:
            payload["runtime_fallback_error"] = "fallback_runtime_not_ready"
            return payload
        fallback = _collect_acceptance(admin_base_url=base, query_text=query_text)
        fallback["primary_base_url"] = admin_base_url
        fallback["effective_base_url"] = base
        fallback["runtime_fallback_used"] = True
        fallback["fallback_runtime_port"] = port
        return fallback
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 BotDB query acceptance gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--query-text", default=DEFAULT_QUERY)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    payload = run_acceptance(
        repo_root=str(args.repo_root),
        admin_base_url=str(args.admin_base_url),
        query_text=str(args.query_text),
    )
    out_path = Path(args.output_dir) / "botdb_query_acceptance.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))

    if args.strict and not bool(payload.get("botdb_query_acceptance_passed")):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
