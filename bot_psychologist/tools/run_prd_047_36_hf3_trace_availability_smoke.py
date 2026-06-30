from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.36-HF3"
DEV_HEADERS = {
    "X-API-Key": "dev-key-001",
    "X-Device-Fingerprint": "prd-047-36-hf3-smoke",
    "Content-Type": "application/json; charset=utf-8",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any]]:
    response = httpx.request(method, url, headers=headers, json=payload, timeout=timeout)
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text}
    return response.status_code, body if isinstance(body, dict) else {"raw": body}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_smoke(*, backend_base_url: str, frontend_base_url: str) -> dict[str, Any]:
    session_id = f"prd-047-36-hf3-{uuid4().hex[:8]}"
    asked_query = "Мне просто тревожно и хочется спокойно разобрать это по шагам."

    health_status, health_payload = _http_json(
        method="GET",
        url=f"{backend_base_url.rstrip('/')}/api/v1/health",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=30.0,
    )

    frontend_status = 0
    try:
        frontend_status = httpx.get(frontend_base_url.rstrip("/"), timeout=15.0).status_code
    except Exception:
        frontend_status = 0

    ask_status, ask_payload = _http_json(
        method="POST",
        url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
        headers=DEV_HEADERS,
        payload={
            "query": asked_query,
            "session_id": session_id,
            "debug": True,
            "include_path": False,
            "include_feedback_prompt": True,
        },
        timeout=120.0,
    )

    time.sleep(1.0)

    exact_status, exact_payload = _http_json(
        method="GET",
        url=f"{backend_base_url.rstrip('/')}/api/debug/session/{session_id}/multiagent-trace?turn_index=1",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=30.0,
    )

    missing_status, missing_payload = _http_json(
        method="GET",
        url=f"{backend_base_url.rstrip('/')}/api/debug/session/{session_id}/multiagent-trace?turn_index=999",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=30.0,
    )

    exact_availability = _safe_dict(exact_payload.get("trace_availability"))
    missing_availability = _safe_dict(missing_payload.get("trace_availability"))

    verdict = "PASS"
    warnings: list[str] = []
    if health_status != 200:
        verdict = "FAIL"
        warnings.append("backend_health_not_200")
    if frontend_status != 200:
        verdict = "FAIL"
        warnings.append("frontend_not_200")
    if ask_status != 200:
        verdict = "FAIL"
        warnings.append("adaptive_turn_failed")
    if exact_status != 200 or exact_availability.get("status") != "available":
        verdict = "FAIL"
        warnings.append("exact_trace_lookup_failed")
    if missing_status != 404 or missing_availability.get("status") != "unavailable":
        verdict = "FAIL"
        warnings.append("missing_turn_contract_failed")
    if exact_availability.get("exact_turn_match") is not True:
        warnings.append("exact_turn_match_not_true")
        if verdict == "PASS":
            verdict = "PASS_WITH_WARNING"

    return {
        "verdict": verdict,
        "warnings": warnings,
        "session_id": session_id,
        "asked_query": asked_query,
        "backend_health_status": health_status,
        "backend_health_payload": health_payload,
        "frontend_status": frontend_status,
        "adaptive_status": ask_status,
        "adaptive_answer_preview": str(ask_payload.get("answer", ""))[:280],
        "exact_trace_status": exact_status,
        "exact_trace_availability": exact_availability,
        "exact_trace_turn_index": exact_payload.get("turn_index"),
        "missing_trace_status": missing_status,
        "missing_trace_availability": missing_availability,
        "missing_trace_detail": missing_payload.get("detail"),
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    backend_base_url = "http://127.0.0.1:8001"
    frontend_base_url = "http://localhost:3000"
    result = run_smoke(
        backend_base_url=backend_base_url,
        frontend_base_url=frontend_base_url,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "live_smoke_result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("verdict", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
