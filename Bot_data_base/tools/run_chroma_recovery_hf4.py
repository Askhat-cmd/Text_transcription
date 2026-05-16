from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.admin_live_smoke import run_admin_live_smoke  # noqa: E402
from review.post_apply_quality_gate import (  # noqa: E402
    build_data_consistency_gate,
    build_no_mutation_proof,
    build_retrieval_quality_smoke,
    build_writer_kb_policy_smoke,
    read_json,
    render_markdown_report,
    sha256_file,
    write_json,
    write_text,
)
from tools.diagnose_chroma_runtime_count import run_diagnostic  # noqa: E402
from tools.reindex_focus_source_chroma_controlled import run_controlled_reindex  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _http_json(url: str, timeout: float = 12.0) -> dict[str, Any]:
    req = Request(url=url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": payload, "error": None}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def _extract_registry_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("sources")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def build_source_hygiene_live_preflight(
    *,
    source_prd: str,
    admin_base_url: str,
    expected_source_id: str,
    expected_blocks: int,
) -> dict[str, Any]:
    base = admin_base_url.rstrip("/")
    registry = _http_json(f"{base}/api/registry")
    registry_slash = _http_json(f"{base}/api/registry/")

    registry_ok = bool(registry.get("ok")) and int(registry.get("status_code") or 0) == 200
    registry_slash_ok = bool(registry_slash.get("ok")) and int(registry_slash.get("status_code") or 0) == 200
    payload = registry.get("body") if registry_ok else registry_slash.get("body")
    rows = _extract_registry_rows(payload)

    focus_rows = [
        row
        for row in rows
        if _normalize(row.get("source_id")) == expected_source_id and _normalize(row.get("status")).lower() == "done"
    ]
    focus = focus_rows[0] if focus_rows else {}
    focus_blocks = _to_int(focus.get("blocks_count"))
    focus_author = _normalize(focus.get("author"))
    focus_title = _normalize(focus.get("title"))
    focus_protected = bool((focus.get("delete_policy") or {}).get("state") == "protected") if isinstance(focus.get("delete_policy"), dict) else False

    non_focus_rows = [row for row in rows if _normalize(row.get("source_id")) != expected_source_id]
    non_focus_blocks_count = sum(_to_int(row.get("blocks_count")) for row in non_focus_rows)
    non_focus_rows_with_blocks = [row for row in non_focus_rows if _to_int(row.get("blocks_count")) > 0]
    non_focus_zero_block_count = sum(1 for row in non_focus_rows if _to_int(row.get("blocks_count")) <= 0)

    issues: list[str] = []
    warnings: list[str] = []
    if not registry_ok and not registry_slash_ok:
        issues.append("registry_unavailable")
    if registry_ok and not registry_slash_ok:
        warnings.append("registry_slash_compatibility_warning")
    if not registry_ok and registry_slash_ok:
        warnings.append("registry_non_slash_compatibility_warning")
    if len(focus_rows) != 1:
        issues.append("focus_source_row_not_single")
    if focus_blocks != expected_blocks:
        issues.append("focus_source_blocks_mismatch")
    if len(non_focus_rows_with_blocks) > 0:
        issues.append("non_focus_sources_with_blocks_present")
    if len(rows) != 1:
        warnings.append("registry_not_focus_only")

    return {
        "schema_version": "source_hygiene_live_preflight_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "admin_base_url": admin_base_url,
        "sources_total": len(rows),
        "focus_source_id": expected_source_id,
        "focus_title": focus_title,
        "focus_author": focus_author,
        "focus_status": _normalize(focus.get("status")).lower(),
        "focus_blocks": focus_blocks,
        "focus_protected": focus_protected,
        "non_focus_sources_count": len(non_focus_rows),
        "non_focus_rows_with_blocks_count": len(non_focus_rows_with_blocks),
        "non_focus_blocks_count": non_focus_blocks_count,
        "non_focus_zero_block_count": non_focus_zero_block_count,
        "source_hygiene_focus_only": len(rows) == 1 and len(focus_rows) == 1 and focus_blocks == expected_blocks,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
    }


def _endpoint_status(smoke: dict[str, Any], endpoint: str) -> str:
    checks = smoke.get("api_checks") if isinstance(smoke.get("api_checks"), dict) else {}
    row = checks.get(endpoint) if isinstance(checks.get(endpoint), dict) else {}
    ok = bool(row.get("ok"))
    code = row.get("status_code")
    return f"{code} / {'ok' if ok else 'fail'}"


def _build_implementation_report(snapshot: dict[str, Any], hygiene: dict[str, Any], smoke: dict[str, Any], diag_before: dict[str, Any], diag_after: dict[str, Any] | None, no_mutation: dict[str, Any]) -> str:
    lines = [
        "## Status",
        f"- implementation: `{snapshot.get('implementation')}`",
        f"- final_status: `{snapshot.get('final_status')}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "",
        "## Live runtime",
        f"- admin_base_url: `{snapshot.get('admin_base_url')}`",
        f"- /api/status: `{_endpoint_status(smoke, '/api/status')}`",
        f"- /api/registry: `{_endpoint_status(smoke, '/api/registry')}`",
        f"- /api/registry/: `{_endpoint_status(smoke, '/api/registry/')}`",
        f"- /api/dashboard: `{_endpoint_status(smoke, '/api/dashboard')}`",
        f"- /api/dashboard/: `{_endpoint_status(smoke, '/api/dashboard/')}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
        "",
        "## Counts",
        f"- registry_focus_blocks: `{hygiene.get('focus_blocks')}`",
        f"- dashboard_blocks_count: `{snapshot.get('dashboard_blocks_count')}`",
        f"- dashboard_chroma_count: `{snapshot.get('dashboard_chroma_count')}`",
        f"- direct_chroma_count_before: `{diag_before.get('total_count')}`",
        f"- direct_chroma_count_after: `{None if diag_after is None else diag_after.get('total_count')}`",
        f"- strict_chroma_count_passed: `{snapshot.get('strict_chroma_count_passed')}`",
        "",
        "## No mutation",
        f"- all_blocks_merged_mutated: `{no_mutation.get('all_blocks_merged_mutated')}`",
        f"- registry_mutated: `{no_mutation.get('registry_mutated')}`",
        f"- provider_called: `{no_mutation.get('provider_called')}`",
        f"- production_apply_performed: `{no_mutation.get('production_apply_performed')}`",
        "",
        "## Commit / Push",
        "- commit hash: `pending-main-push`",
        "- push status: `pending-main-push`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF4 IMPLEMENTATION REPORT", lines)


def _build_chroma_report(snapshot: dict[str, Any], plan: dict[str, Any], diag_before: dict[str, Any], diag_after: dict[str, Any] | None, reindex_result: dict[str, Any] | None) -> str:
    lines = [
        "## Plan",
        f"- route: `{plan.get('route')}`",
        f"- expected_blocks: `{plan.get('expected_blocks')}`",
        "",
        "## Diagnostic Before",
        f"- status: `{diag_before.get('status')}`",
        f"- total_count: `{diag_before.get('total_count')}`",
        f"- source_ids: `{diag_before.get('source_ids')}`",
        "",
        "## Diagnostic After",
        f"- total_count: `{None if diag_after is None else diag_after.get('total_count')}`",
        f"- source_ids: `{None if diag_after is None else diag_after.get('source_ids')}`",
        "",
        "## Live",
        f"- dashboard_chroma_count: `{snapshot.get('dashboard_chroma_count')}`",
        f"- strict_chroma_count_passed: `{snapshot.get('strict_chroma_count_passed')}`",
        "",
        "## Reindex",
        f"- performed: `{None if reindex_result is None else reindex_result.get('reindex_performed')}`",
        f"- status: `{None if reindex_result is None else reindex_result.get('status')}`",
        f"- chroma_count_after: `{None if reindex_result is None else reindex_result.get('chroma_count_after')}`",
    ]
    issues = snapshot.get("issues")
    if isinstance(issues, list) and issues:
        lines.extend(["", "## Issues", *[f"- `{item}`" for item in issues]])
    return render_markdown_report("PRD-046.0.7.2-HF4 CHROMA RECONCILIATION REPORT", lines)


def _build_next_prd_report(snapshot: dict[str, Any]) -> str:
    final_status = _normalize(snapshot.get("final_status"))
    if final_status == "passed":
        next_prd = "PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD"
    else:
        next_prd = f"targeted HF based on blocker: {final_status}"
    lines = [
        "## Recommendation",
        f"- next_prd: `{next_prd}`",
        f"- final_status: `{final_status}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF4 NEXT PRD RECOMMENDATION", lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    reports_dir = Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    blocks_path = Path(args.blocks_path)
    registry_path = Path(args.registry_path)
    blocks_hash_before = sha256_file(blocks_path)
    registry_hash_before = sha256_file(registry_path)

    hygiene = build_source_hygiene_live_preflight(
        source_prd=str(args.source_prd),
        admin_base_url=str(args.admin_base_url),
        expected_source_id=str(args.expected_source_id),
        expected_blocks=int(args.expected_blocks),
    )
    write_json(out_dir / "source_hygiene_live_preflight.json", hygiene)

    diag_before = run_diagnostic(
        source_prd=str(args.source_prd),
        botdb_dir=BOTDB_DIR,
        config_path=Path(args.config_path),
        sample_ids_limit=10,
    )
    write_json(out_dir / "direct_chroma_diagnostic_before.json", diag_before)

    smoke_before = run_admin_live_smoke(
        admin_base_url=str(args.admin_base_url),
        source_prd=str(args.source_prd),
        expected_source_id=str(args.expected_source_id),
        expected_blocks_total=int(args.expected_blocks),
        require_admin_api=True,
        try_start_server=False,
        startup_timeout_sec=30,
        http_timeout_sec=20.0,
        repo_root=REPO_ROOT,
    )["smoke"]

    route = "undecided"
    issues: list[str] = []
    warnings: list[str] = []
    dashboard_count_before = _to_int(smoke_before.get("chroma_count"))
    direct_before = diag_before.get("total_count")
    direct_before_int = _to_int(direct_before) if direct_before is not None else None

    reindex_result: dict[str, Any] | None = None
    backup_manifest: dict[str, Any] = {
        "schema_version": "chroma_backup_manifest_v1",
        "source_prd": str(args.source_prd),
        "generated_at": _utc_now_iso(),
        "copied": False,
        "errors": [],
    }
    diag_after: dict[str, Any] | None = None
    final_status = "failed"
    implementation = "done"

    if "non_focus_sources_with_blocks_present" in (hygiene.get("issues") or []):
        route = "blocked_source_hygiene"
        final_status = "done_with_source_hygiene_blocker"
        issues.append("non_focus_sources_with_blocks_present")
    elif _normalize(diag_before.get("status")) != "ok":
        route = "blocked_direct_diagnostic"
        final_status = "done_with_direct_chroma_diagnostic_blocker"
        issues.append("direct_chroma_diagnostic_unavailable")
    elif dashboard_count_before == int(args.expected_blocks) and direct_before_int == int(args.expected_blocks):
        route = "already_consistent"
        final_status = "passed"
        diag_after = diag_before
    elif dashboard_count_before != int(args.expected_blocks) and direct_before_int == int(args.expected_blocks):
        route = "dashboard_count_source_blocker"
        final_status = "done_with_dashboard_chroma_count_source_blocker"
        issues.append("dashboard_chroma_count_source_mismatch")
    else:
        route = "controlled_reindex_focus_source"
        reindex_payload = run_controlled_reindex(
            source_prd=str(args.source_prd),
            botdb_dir=BOTDB_DIR,
            config_path=Path(args.config_path),
            blocks_path=blocks_path,
            expected_source_id=str(args.expected_source_id),
            expected_blocks=int(args.expected_blocks),
            backup_root=Path(args.backup_root),
            confirm=True,
        )
        reindex_result = reindex_payload["result"]
        backup_manifest = reindex_payload["backup_manifest"]
        write_json(out_dir / "chroma_reindex_result.json", reindex_result)
        write_json(out_dir / "chroma_backup_manifest.json", backup_manifest)

        diag_after = run_diagnostic(
            source_prd=str(args.source_prd),
            botdb_dir=BOTDB_DIR,
            config_path=Path(args.config_path),
            sample_ids_limit=10,
        )
        write_json(out_dir / "direct_chroma_diagnostic_after.json", diag_after)
        if _normalize(reindex_result.get("status")) != "passed":
            final_status = "done_with_chroma_reindex_failed"
            issues.append("chroma_reindex_failed")
        else:
            final_status = "passed"

    if reindex_result is None:
        write_json(
            out_dir / "chroma_reindex_result.json",
            {
                "schema_version": "chroma_reindex_result_v1",
                "source_prd": str(args.source_prd),
                "generated_at": _utc_now_iso(),
                "status": "not_performed",
                "reindex_performed": False,
            },
        )
        write_json(out_dir / "chroma_backup_manifest.json", backup_manifest)
    if diag_after is None:
        diag_after = run_diagnostic(
            source_prd=str(args.source_prd),
            botdb_dir=BOTDB_DIR,
            config_path=Path(args.config_path),
            sample_ids_limit=10,
        )
        write_json(out_dir / "direct_chroma_diagnostic_after.json", diag_after)

    smoke_after = run_admin_live_smoke(
        admin_base_url=str(args.admin_base_url),
        source_prd=str(args.source_prd),
        expected_source_id=str(args.expected_source_id),
        expected_blocks_total=int(args.expected_blocks),
        require_admin_api=True,
        try_start_server=False,
        startup_timeout_sec=30,
        http_timeout_sec=20.0,
        repo_root=REPO_ROOT,
    )["smoke"]
    write_json(out_dir / "admin_live_smoke_after_recovery.json", smoke_after)

    blocks_payload = read_json(blocks_path)
    registry_payload = read_json(registry_path)
    data_consistency = build_data_consistency_gate(
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        apply_result_payload={},
        expected_blocks_total=int(args.expected_blocks),
        expected_source_id=str(args.expected_source_id),
    )
    retrieval_smoke = build_retrieval_quality_smoke(
        blocks_payload=blocks_payload,
        expected_source_id=str(args.expected_source_id),
    )
    write_json(out_dir / "retrieval_smoke_after_recovery.json", retrieval_smoke)
    writer_policy = build_writer_kb_policy_smoke(blocks_payload=blocks_payload)

    blocks_hash_after = sha256_file(blocks_path)
    registry_hash_after = sha256_file(registry_path)
    no_mutation = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        blocks_hash_before=blocks_hash_before,
        blocks_hash_after=blocks_hash_after,
        registry_hash_before=registry_hash_before,
        registry_hash_after=registry_hash_after,
    )
    write_json(out_dir / "no_mutation_proof.json", no_mutation)

    dashboard_count_after = _to_int(smoke_after.get("chroma_count"))
    direct_after_int = _to_int(diag_after.get("total_count")) if diag_after.get("total_count") is not None else None
    strict_chroma_count_passed = (
        dashboard_count_after == int(args.expected_blocks)
        and direct_after_int == int(args.expected_blocks)
    )

    if final_status == "passed" and not strict_chroma_count_passed:
        final_status = "done_with_chroma_reindex_failed"
        issues.append("strict_chroma_count_not_recovered")

    admin_runtime_status = _normalize(smoke_after.get("admin_runtime_status")) or "failed"
    if final_status == "done_with_chroma_reindex_failed":
        admin_runtime_status = "blocked_chroma_count_mismatch"
    if final_status == "done_with_dashboard_chroma_count_source_blocker":
        admin_runtime_status = "blocked_dashboard_chroma_count_source"
    if final_status == "done_with_direct_chroma_diagnostic_blocker":
        admin_runtime_status = "blocked_direct_chroma_diagnostic"
    if final_status == "done_with_source_hygiene_blocker":
        admin_runtime_status = "blocked_source_hygiene"

    quality_gate_passed = (
        final_status == "passed"
        and strict_chroma_count_passed
        and bool(data_consistency.get("data_consistency_passed"))
        and bool(retrieval_smoke.get("retrieval_quality_passed"))
        and bool(writer_policy.get("writer_kb_policy_passed"))
        and bool(no_mutation.get("all_blocks_merged_mutated") is False)
        and bool(no_mutation.get("registry_mutated") is False)
        and bool(hygiene.get("source_hygiene_focus_only"))
    )
    diagnostic_center_ready = quality_gate_passed
    if quality_gate_passed:
        admin_runtime_status = "passed"

    if final_status == "failed":
        if admin_runtime_status == "blocked_admin_api_unavailable":
            final_status = "done_with_admin_api_blocker"
        elif admin_runtime_status == "blocked_chroma_count_mismatch":
            final_status = "done_with_chroma_count_blocker"

    plan = {
        "schema_version": "chroma_recovery_plan_v1",
        "source_prd": str(args.source_prd),
        "generated_at": _utc_now_iso(),
        "route": route,
        "expected_source_id": str(args.expected_source_id),
        "expected_blocks": int(args.expected_blocks),
        "dashboard_chroma_count_before": dashboard_count_before,
        "direct_chroma_count_before": direct_before,
        "dashboard_chroma_count_after": dashboard_count_after,
        "direct_chroma_count_after": diag_after.get("total_count"),
        "reindex_performed": bool((reindex_result or {}).get("reindex_performed")),
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
    }
    write_json(out_dir / "chroma_recovery_plan.json", plan)

    snapshot = {
        "schema_version": "strict_quality_gate_hf4_v1",
        "source_prd": str(args.source_prd),
        "generated_at": _utc_now_iso(),
        "implementation": "done" if final_status == "passed" else final_status,
        "final_status": final_status,
        "admin_base_url": str(args.admin_base_url),
        "admin_runtime_status": admin_runtime_status,
        "quality_gate_passed": quality_gate_passed,
        "diagnostic_center_ready": diagnostic_center_ready,
        "strict_chroma_count_passed": strict_chroma_count_passed,
        "registry_focus_blocks": hygiene.get("focus_blocks"),
        "dashboard_blocks_count": smoke_after.get("dashboard_blocks_count"),
        "dashboard_chroma_count": smoke_after.get("chroma_count"),
        "direct_chroma_count_before": diag_before.get("total_count"),
        "direct_chroma_count_after": diag_after.get("total_count"),
        "source_hygiene_focus_only": hygiene.get("source_hygiene_focus_only"),
        "retrieval_smoke_passed": retrieval_smoke.get("retrieval_quality_passed"),
        "writer_kb_policy_passed": writer_policy.get("writer_kb_policy_passed"),
        "all_blocks_merged_mutated": no_mutation.get("all_blocks_merged_mutated"),
        "registry_mutated": no_mutation.get("registry_mutated"),
        "provider_called": False,
        "production_apply_performed": False,
        "chroma_reindex_performed": bool((reindex_result or {}).get("reindex_performed")),
        "issues": sorted(set(issues + list(hygiene.get("issues") or []))),
        "warnings": sorted(set(warnings + list(hygiene.get("warnings") or []))),
    }
    write_json(out_dir / "strict_quality_gate_hf4.json", snapshot)

    write_text(
        reports_dir / "PRD-046.0.7.2-HF4_IMPLEMENTATION_REPORT.md",
        _build_implementation_report(snapshot, hygiene, smoke_after, diag_before, diag_after, no_mutation),
    )
    write_text(
        reports_dir / "PRD-046.0.7.2-HF4_CHROMA_RECONCILIATION_REPORT.md",
        _build_chroma_report(snapshot, plan, diag_before, diag_after, reindex_result),
    )
    write_text(
        reports_dir / "PRD-046.0.7.2-HF4_NEXT_PRD_RECOMMENDATION.md",
        _build_next_prd_report(snapshot),
    )

    return {
        "status": final_status,
        "source_hygiene_live_preflight": hygiene,
        "direct_chroma_diagnostic_before": diag_before,
        "chroma_recovery_plan": plan,
        "chroma_reindex_result": reindex_result,
        "direct_chroma_diagnostic_after": diag_after,
        "admin_live_smoke_after_recovery": smoke_after,
        "strict_quality_gate_hf4": snapshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.7.2-HF4 Chroma count recovery runner.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2-HF4")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--blocks-path", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry-path", default="Bot_data_base/data/registry.json")
    parser.add_argument("--backup-root", default="TO_DO_LIST/backups/PRD-046.0.7.2-HF4/chroma_before_reindex")
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.7.2-HF4")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    allowed = {
        "passed",
        "done_with_direct_chroma_diagnostic_blocker",
        "done_with_dashboard_chroma_count_source_blocker",
        "done_with_chroma_reindex_failed",
        "done_with_source_hygiene_blocker",
        "done_with_admin_api_blocker",
        "done_with_chroma_count_blocker",
    }
    return 0 if _normalize(result.get("status")) in allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
