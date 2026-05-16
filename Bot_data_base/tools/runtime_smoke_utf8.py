from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:8003"
DEFAULT_RUNTIME_OUTPUT = "TO_DO_LIST/logs/PRD-046.0.10-HF1/runtime_smoke_utf8.json"
DEFAULT_UTF8_CHECK_OUTPUT = "TO_DO_LIST/logs/PRD-046.0.10-HF1/utf8_artifact_check.json"
DEFAULT_SOURCE_PRD = "PRD-046.0.10-HF1"

MOJIBAKE_MARKERS = ("\u0413\u0452", "\u0413\u2018", "\\u0085")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_body(data: bytes, headers: Any) -> str:
    content_type = str(headers.get("Content-Type", "") or "").lower()
    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return data.decode(charset, errors="strict")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _fetch_json(url: str, timeout_sec: int = 15) -> tuple[dict[str, Any] | list[Any] | None, dict[str, Any]]:
    request = Request(url=url, method="GET")
    try:
        with urlopen(request, timeout=timeout_sec) as response:  # nosec B310: local trusted admin endpoint
            body_text = _decode_body(response.read(), response.headers)
            status_code = int(getattr(response, "status", 200))
            parsed = None
            error = None
            try:
                parsed = json.loads(body_text)
            except Exception as exc:
                error = f"json_decode_error: {exc}"
            return parsed, {
                "ok": status_code == 200 and error is None,
                "status_code": status_code,
                "error": error,
            }
    except HTTPError as exc:
        return None, {"ok": False, "status_code": int(exc.code), "error": str(exc)}
    except URLError as exc:
        return None, {"ok": False, "status_code": None, "error": str(exc)}
    except Exception as exc:
        return None, {"ok": False, "status_code": None, "error": str(exc)}


def _extract_focus_identity(registry_payload: Any) -> dict[str, str]:
    if not isinstance(registry_payload, dict):
        return {"source_id": "", "title": "", "author": ""}
    rows = registry_payload.get("sources")
    if not isinstance(rows, list):
        return {"source_id": "", "title": "", "author": ""}

    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id", "") or "")
        if "кузниц" in source_id.lower() and "дух" in source_id.lower():
            return {
                "source_id": source_id,
                "title": str(row.get("title", "") or ""),
                "author": str(row.get("author", "") or ""),
            }
    return {"source_id": "", "title": "", "author": ""}


def _find_mojibake_markers(payload: Any, markers: tuple[str, ...] = MOJIBAKE_MARKERS) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def _walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                _walk(item, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                _walk(item, f"{path}[{idx}]")
            return
        if not isinstance(value, str):
            return

        for marker in markers:
            if marker in value:
                findings.append({"path": path, "marker": marker, "snippet": value[:160]})
        if "\u0085" in value:
            findings.append({"path": path, "marker": "\\u0085", "snippet": value[:160]})

    _walk(payload, "")
    return findings


def build_runtime_smoke_utf8_payload(*, base_url: str, source_prd: str) -> dict[str, Any]:
    endpoints = ["/api/status", "/api/registry", "/api/registry/", "/api/dashboard", "/api/dashboard/"]
    checks: dict[str, Any] = {}
    payloads: dict[str, Any] = {}
    for endpoint in endpoints:
        body, meta = _fetch_json(f"{base_url}{endpoint}")
        checks[endpoint] = meta
        payloads[endpoint] = body

    dashboard_payload = payloads.get("/api/dashboard")
    if not isinstance(dashboard_payload, dict):
        dashboard_payload = payloads.get("/api/dashboard/")
    registry_payload = payloads.get("/api/registry/")
    if not isinstance(registry_payload, dict):
        registry_payload = payloads.get("/api/registry")

    focus = _extract_focus_identity(registry_payload)
    sources_total = None
    blocks_count = None
    chroma_count = None
    legacy_sd_active = None
    if isinstance(dashboard_payload, dict):
        sources_total = (dashboard_payload.get("sources") or {}).get("total")
        blocks_count = (dashboard_payload.get("blocks") or {}).get("production_total")
        chroma_count = (dashboard_payload.get("chroma") or {}).get("count")
        legacy_sd_active = (dashboard_payload.get("governance") or {}).get("legacy_sd_active")

    smoke_payload = {
        "schema_version": "runtime_smoke_utf8_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "admin_base_url": base_url,
        "api_checks": checks,
        "summary": {
            "sources_total": sources_total,
            "blocks": blocks_count,
            "chroma": chroma_count,
            "legacy_sd_active": legacy_sd_active,
        },
        "focus_source_identity": focus,
        "russian_text_samples": [
            focus.get("title", ""),
            focus.get("author", ""),
            focus.get("source_id", ""),
        ],
        "raw_payload_excerpt": {
            "registry": registry_payload,
            "dashboard": dashboard_payload,
        },
    }
    return smoke_payload


def build_utf8_check_payload(*, runtime_payload: dict[str, Any], source_prd: str) -> dict[str, Any]:
    findings = _find_mojibake_markers(runtime_payload)
    return {
        "schema_version": "utf8_artifact_check_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "markers_checked": list(MOJIBAKE_MARKERS),
        "mojibake_markers_found": findings,
        "passed": len(findings) == 0,
    }


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build UTF-8 safe BotDB runtime smoke artifacts.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--runtime-output", default=DEFAULT_RUNTIME_OUTPUT)
    parser.add_argument("--utf8-check-output", default=DEFAULT_UTF8_CHECK_OUTPUT)
    args = parser.parse_args()

    runtime_payload = build_runtime_smoke_utf8_payload(base_url=args.base_url, source_prd=args.source_prd)
    utf8_payload = build_utf8_check_payload(runtime_payload=runtime_payload, source_prd=args.source_prd)

    _save_json(Path(args.runtime_output), runtime_payload)
    _save_json(Path(args.utf8_check_output), utf8_payload)

    print(
        json.dumps(
            {
                "runtime_output": args.runtime_output,
                "utf8_check_output": args.utf8_check_output,
                "utf8_passed": utf8_payload["passed"],
                "markers_found_count": len(utf8_payload["mojibake_markers_found"]),
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
