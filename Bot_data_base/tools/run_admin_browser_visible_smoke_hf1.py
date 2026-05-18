from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
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


def _http_request(url: str, *, method: str = "GET", body: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url=url, method=method, data=data, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            parsed: Any
            try:
                parsed = json.loads(raw) if raw else None
            except Exception:
                parsed = raw
            return {
                "ok": True,
                "status_code": int(resp.status),
                "body": parsed,
                "error": None,
            }
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _extract_source_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return [row for row in payload.get("sources") if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def run_browser_visible_smoke(
    *,
    source_prd: str,
    admin_base_url: str,
    expected_source_id: str,
    expected_blocks: int,
) -> dict[str, Any]:
    base = admin_base_url.rstrip("/")
    checks = {
        "dashboard_page": _http_request(f"{base}/"),
        "registry_page": _http_request(f"{base}/registry"),
        "static_app_js": _http_request(f"{base}/static/app.js"),
        "static_registry_js": _http_request(f"{base}/static/registry.js"),
        "dashboard_api": _http_request(f"{base}/api/dashboard"),
        "registry_api": _http_request(f"{base}/api/registry/"),
        "registry_stats_api": _http_request(f"{base}/api/registry/stats"),
    }

    rows = _extract_source_rows((checks["registry_api"] or {}).get("body"))
    focus_rows = [row for row in rows if _normalize(row.get("source_id")) == expected_source_id]
    focus_blocks = _to_int(focus_rows[0].get("blocks_count")) if focus_rows else 0

    dashboard_body = (checks["dashboard_api"] or {}).get("body")
    chroma_block = dashboard_body.get("chroma") if isinstance(dashboard_body, dict) and isinstance(dashboard_body.get("chroma"), dict) else {}
    dashboard_chroma_status = _normalize(chroma_block.get("status")).lower()
    dashboard_chroma_count = _to_int(chroma_block.get("count")) if chroma_block else 0

    stats_body = (checks["registry_stats_api"] or {}).get("body")
    stats_chroma_total = _to_int(stats_body.get("chroma_total")) if isinstance(stats_body, dict) else 0

    result = {
        "schema_version": "admin_browser_visible_smoke_hf1_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "checks": checks,
        "focus_source_id": expected_source_id,
        "focus_source_visible": bool(focus_rows),
        "focus_source_blocks": focus_blocks,
        "dashboard_chroma_status": dashboard_chroma_status or "unknown",
        "dashboard_chroma_count": dashboard_chroma_count,
        "registry_stats_chroma_total": stats_chroma_total,
        "dashboard_page_http_200": bool(checks["dashboard_page"].get("ok")) and int(checks["dashboard_page"].get("status_code") or 0) == 200,
        "registry_page_http_200": bool(checks["registry_page"].get("ok")) and int(checks["registry_page"].get("status_code") or 0) == 200,
        "dashboard_api_http_200": bool(checks["dashboard_api"].get("ok")) and int(checks["dashboard_api"].get("status_code") or 0) == 200,
        "registry_api_http_200": bool(checks["registry_api"].get("ok")) and int(checks["registry_api"].get("status_code") or 0) == 200,
        "registry_stats_http_200": bool(checks["registry_stats_api"].get("ok")) and int(checks["registry_stats_api"].get("status_code") or 0) == 200,
        "dashboard_chroma_unavailable": dashboard_chroma_status == "unavailable",
        "registry_global_error_http_500": int(checks["registry_stats_api"].get("status_code") or 0) >= 500,
        "admin_browser_visible_smoke_passed": False,
        "issues": [],
        "warnings": [],
    }

    issues: list[str] = []
    if not result["dashboard_page_http_200"]:
        issues.append("dashboard_page_not_200")
    if not result["registry_page_http_200"]:
        issues.append("registry_page_not_200")
    if not result["dashboard_api_http_200"]:
        issues.append("dashboard_api_not_200")
    if not result["registry_api_http_200"]:
        issues.append("registry_api_not_200")
    if not result["registry_stats_http_200"]:
        issues.append("registry_stats_not_200")
    if not result["focus_source_visible"]:
        issues.append("focus_source_not_visible")
    if focus_blocks != expected_blocks:
        issues.append("focus_source_blocks_mismatch")
    if dashboard_chroma_count != expected_blocks and stats_chroma_total != expected_blocks:
        issues.append("chroma_count_not_expected")
    if result["dashboard_chroma_unavailable"]:
        issues.append("dashboard_chroma_unavailable")
    if result["registry_global_error_http_500"]:
        issues.append("registry_stats_http_500")

    result["issues"] = sorted(set(issues))
    result["admin_browser_visible_smoke_passed"] = len(result["issues"]) == 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HF1 browser-visible admin smoke runner")
    parser.add_argument("--source-prd", default="PRD-046.1.21-HF1")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--out", default="TO_DO_LIST/logs/PRD-046.1.21-HF1/admin_browser_visible_smoke.json")
    args = parser.parse_args()

    payload = run_browser_visible_smoke(
        source_prd=str(args.source_prd),
        admin_base_url=str(args.admin_base_url),
        expected_source_id=str(args.expected_source_id),
        expected_blocks=int(args.expected_blocks),
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
