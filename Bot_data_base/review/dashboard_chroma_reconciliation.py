from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_dashboard_payload(smoke: dict[str, Any]) -> dict[str, Any]:
    checks = smoke.get("api_checks") if isinstance(smoke.get("api_checks"), dict) else {}
    dashboard = checks.get("/api/dashboard") if isinstance(checks.get("/api/dashboard"), dict) else {}
    body = dashboard.get("body")
    return body if isinstance(body, dict) else {}


def _extract_dashboard_chroma_status(payload: dict[str, Any]) -> str | None:
    chroma = payload.get("chroma") if isinstance(payload.get("chroma"), dict) else {}
    status = chroma.get("status")
    if status is None:
        return None
    raw = str(status).strip()
    return raw or None


def _extract_dashboard_indexed_source_ids(payload: dict[str, Any]) -> list[str]:
    chroma = payload.get("chroma") if isinstance(payload.get("chroma"), dict) else {}
    rows = chroma.get("indexed_source_ids") if isinstance(chroma.get("indexed_source_ids"), list) else []
    result: list[str] = []
    for item in rows:
        value = str(item or "").strip()
        if value:
            result.append(value)
    return sorted(set(result))


def build_chroma_count_reconciliation(
    *,
    source_prd: str,
    admin_base_url: str,
    smoke: dict[str, Any],
    expected_source_id: str,
    expected_blocks: int,
    direct_chroma_count: int | None,
    historical_chroma_count: int | None,
    historical_proof_path: str | None,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    dashboard_payload = _extract_dashboard_payload(smoke)
    dashboard_chroma_status = _extract_dashboard_chroma_status(dashboard_payload)
    dashboard_indexed_source_ids = _extract_dashboard_indexed_source_ids(dashboard_payload)
    registry_focus_blocks = _to_int(smoke.get("focus_blocks_count")) or 0
    dashboard_blocks_count = _to_int(smoke.get("dashboard_blocks_count"))
    dashboard_chroma_count = _to_int(smoke.get("chroma_count"))

    if registry_focus_blocks != expected_blocks:
        issues.append("registry_focus_blocks_mismatch")
    if dashboard_blocks_count != expected_blocks:
        issues.append("dashboard_blocks_count_mismatch")
    if dashboard_chroma_status is None:
        issues.append("dashboard_chroma_status_missing")
    elif dashboard_chroma_status.lower() != "ok":
        issues.append("dashboard_chroma_status_not_ok")
    if dashboard_chroma_count is None:
        issues.append("dashboard_chroma_schema_missing")
    elif dashboard_chroma_count != expected_blocks:
        issues.append("dashboard_chroma_count_mismatch")
    if expected_source_id not in dashboard_indexed_source_ids:
        issues.append("dashboard_chroma_indexed_source_missing")

    if historical_chroma_count is not None and dashboard_chroma_count is not None and historical_chroma_count != dashboard_chroma_count:
        warnings.append("historical_chroma_count_differs_from_live")
    if "dashboard_chroma_count_mismatch" in issues and historical_chroma_count is not None:
        warnings.append("historical_proof_cannot_override_live_dashboard_mismatch")

    reconciliation_status = "passed_strict_chroma_reconciliation"
    if issues:
        if "dashboard_chroma_schema_missing" in issues:
            reconciliation_status = "blocked_dashboard_chroma_schema_missing"
        elif "dashboard_chroma_count_mismatch" in issues:
            if direct_chroma_count is None:
                reconciliation_status = "blocked_live_dashboard_chroma_mismatch"
            elif direct_chroma_count == expected_blocks:
                reconciliation_status = "blocked_dashboard_count_source_mismatch"
            elif direct_chroma_count == dashboard_chroma_count:
                reconciliation_status = "blocked_actual_chroma_count_mismatch"
            else:
                reconciliation_status = "blocked_live_direct_chroma_mismatch"
        else:
            reconciliation_status = "blocked_dashboard_contract_mismatch"

    strict_gate_passed = len(issues) == 0
    return {
        "schema_version": "dashboard_chroma_count_reconciliation_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "expected_source_id": expected_source_id,
        "expected_blocks": expected_blocks,
        "registry_focus_blocks": registry_focus_blocks,
        "dashboard_blocks_count": dashboard_blocks_count,
        "dashboard_chroma_status": dashboard_chroma_status,
        "dashboard_chroma_count": dashboard_chroma_count,
        "dashboard_indexed_source_ids": dashboard_indexed_source_ids,
        "direct_chroma_count": direct_chroma_count,
        "historical_chroma_count": historical_chroma_count,
        "historical_proof_path": historical_proof_path,
        "reconciliation_status": reconciliation_status,
        "strict_gate_passed": strict_gate_passed,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
    }
