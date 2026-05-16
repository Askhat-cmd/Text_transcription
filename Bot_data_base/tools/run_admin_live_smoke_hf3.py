from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.admin_live_smoke import run_admin_live_smoke  # noqa: E402
from review.dashboard_chroma_reconciliation import build_chroma_count_reconciliation  # noqa: E402
from review.post_apply_quality_gate import (  # noqa: E402
    build_apply_route_consistency,
    build_data_consistency_gate,
    build_no_mutation_proof,
    build_quality_gate_snapshot,
    build_retrieval_quality_smoke,
    build_writer_kb_policy_smoke,
    read_json,
    render_markdown_report,
    sha256_file,
    write_json,
    write_text,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_shape(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        return {"type": type(value).__name__}
    if isinstance(value, dict):
        keys = sorted(value.keys())[:40]
        return {
            "type": "dict",
            "keys_count": len(value),
            "keys": {key: _safe_shape(value.get(key), depth + 1) for key in keys},
        }
    if isinstance(value, list):
        item_shape = _safe_shape(value[0], depth + 1) if value else None
        return {"type": "list", "length": len(value), "item_shape": item_shape}
    if isinstance(value, str):
        return {"type": "str", "length": len(value)}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, int):
        return {"type": "int"}
    if isinstance(value, float):
        return {"type": "float"}
    if value is None:
        return {"type": "null"}
    return {"type": type(value).__name__}


def _endpoint_status(smoke: dict[str, Any], endpoint: str) -> str:
    payload = (smoke.get("api_checks") or {}).get(endpoint) if isinstance(smoke.get("api_checks"), dict) else None
    if not isinstance(payload, dict):
        return "n/a"
    code = payload.get("status_code")
    ok = bool(payload.get("ok"))
    return f"{code} / {'ok' if ok else 'fail'}"


def _extract_count(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    for key in ("dashboard_chroma_count", "registry_chroma_count", "chroma_count", "chroma_count_after", "count"):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _load_historical_chroma_count() -> tuple[int | None, str | None]:
    candidates = [
        REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.9-RUN1-HF3" / "chroma_admin_runtime_diagnostic.json",
        REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.7.1" / "admin_runtime_smoke.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        count = _extract_count(payload)
        if count is not None:
            return count, str(path.relative_to(REPO_ROOT))
    return None, None


def _read_direct_chroma_count() -> tuple[int | None, str | None]:
    config_path = REPO_ROOT / "Bot_data_base" / "config.yaml"
    if not config_path.exists():
        return None, "config_not_found"
    try:
        import yaml  # type: ignore
    except Exception:
        return None, "pyyaml_not_available"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return None, f"config_parse_error:{exc}"

    storage = config.get("storage") if isinstance(config.get("storage"), dict) else {}
    db_rel = str(storage.get("chroma_db_path") or "data/chroma_db")
    collection_name = str(storage.get("collection_name") or "bot_knowledge_base")
    db_path = (REPO_ROOT / "Bot_data_base" / db_rel).resolve()

    try:
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore
    except Exception:
        return None, "chromadb_not_available"
    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False, allow_reset=True))
        collection = client.get_or_create_collection(name=collection_name)
        count = int(collection.count())
        return count, None
    except Exception as exc:
        return None, f"direct_chroma_count_error:{exc}"


def _build_payload_shape_sanitized_hf3(smoke: dict[str, Any]) -> dict[str, Any]:
    checks = smoke.get("api_checks") if isinstance(smoke.get("api_checks"), dict) else {}
    payload_shapes: dict[str, Any] = {}
    for endpoint in ("/api/status", "/api/registry", "/api/registry/", "/api/dashboard", "/api/dashboard/"):
        payload = checks.get(endpoint) if isinstance(checks.get(endpoint), dict) else {}
        payload_shapes[endpoint] = {
            "status_code": payload.get("status_code"),
            "ok": bool(payload.get("ok")),
            "body_shape": _safe_shape(payload.get("body")),
            "error_type": type(payload.get("error")).__name__ if payload.get("error") is not None else None,
        }
    return {
        "schema_version": "admin_payload_shape_sanitized_hf3_v1",
        "source_prd": "PRD-046.0.7.2-HF3",
        "generated_at": _utc_now_iso(),
        "payload_shapes": payload_shapes,
    }


def _implementation_report(
    snapshot: dict[str, Any],
    smoke: dict[str, Any],
    reconciliation: dict[str, Any],
    no_mutation: dict[str, Any],
) -> str:
    final_status = str(snapshot.get("final_status") or "failed")
    implementation_status = "done" if final_status == "passed" else "done_with_chroma_count_blocker" if final_status == "done_with_chroma_count_blocker" else final_status
    lines = [
        "## Status",
        f"- implementation: `{implementation_status}`",
        f"- final_status: `{final_status}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "",
        "## Admin runtime",
        f"- admin_base_url: `{smoke.get('admin_base_url')}`",
        f"- server_launch_mode: `{smoke.get('server_launch_mode')}`",
        f"- /api/status: `{_endpoint_status(smoke, '/api/status')}`",
        f"- /api/registry: `{_endpoint_status(smoke, '/api/registry')}`",
        f"- /api/registry/: `{_endpoint_status(smoke, '/api/registry/')}`",
        f"- /api/dashboard: `{_endpoint_status(smoke, '/api/dashboard')}`",
        f"- /api/dashboard/: `{_endpoint_status(smoke, '/api/dashboard/')}`",
        f"- admin_runtime_status: `{smoke.get('admin_runtime_status')}`",
        "",
        "## Counts",
        f"- registry_focus_blocks: `{reconciliation.get('registry_focus_blocks')}`",
        f"- dashboard_blocks_count: `{reconciliation.get('dashboard_blocks_count')}`",
        f"- dashboard_chroma_count: `{reconciliation.get('dashboard_chroma_count')}`",
        f"- direct_chroma_count: `{reconciliation.get('direct_chroma_count')}`",
        f"- historical_chroma_count: `{reconciliation.get('historical_chroma_count')}`",
        f"- strict_chroma_count_passed: `{reconciliation.get('strict_gate_passed')}`",
        "",
        "## No mutation",
        f"- all_blocks_merged_mutated: `{no_mutation.get('all_blocks_merged_mutated')}`",
        f"- registry_mutated: `{no_mutation.get('registry_mutated')}`",
        f"- provider_called: `{no_mutation.get('provider_called')}`",
        f"- chroma_reindex_performed: `{no_mutation.get('chroma_reindex_performed')}`",
        f"- production_apply_performed: `{no_mutation.get('production_apply_performed')}`",
        "",
        "## Commit / Push",
        "- commit hash: `pending-main-push`",
        "- push status: `pending-main-push`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF3 IMPLEMENTATION REPORT", lines)


def _chroma_reconciliation_report(reconciliation: dict[str, Any]) -> str:
    lines = [
        "## Contract",
        f"- expected_source_id: `{reconciliation.get('expected_source_id')}`",
        f"- expected_blocks: `{reconciliation.get('expected_blocks')}`",
        "",
        "## Observed",
        f"- registry_focus_blocks: `{reconciliation.get('registry_focus_blocks')}`",
        f"- dashboard_blocks_count: `{reconciliation.get('dashboard_blocks_count')}`",
        f"- dashboard_chroma_status: `{reconciliation.get('dashboard_chroma_status')}`",
        f"- dashboard_chroma_count: `{reconciliation.get('dashboard_chroma_count')}`",
        f"- direct_chroma_count: `{reconciliation.get('direct_chroma_count')}`",
        f"- historical_chroma_count: `{reconciliation.get('historical_chroma_count')}`",
        "",
        "## Result",
        f"- reconciliation_status: `{reconciliation.get('reconciliation_status')}`",
        f"- strict_gate_passed: `{reconciliation.get('strict_gate_passed')}`",
    ]
    issues = reconciliation.get("issues")
    if isinstance(issues, list) and issues:
        lines.extend(["", "## Issues", *[f"- `{item}`" for item in issues]])
    warnings = reconciliation.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.extend(["", "## Warnings", *[f"- `{item}`" for item in warnings]])
    if reconciliation.get("strict_gate_passed"):
        lines.extend(["", "## Recommendation", "- `PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD`"])
    else:
        lines.extend(["", "## Recommendation", "- `PRD-046.0.7.2-HF4 - Chroma Count Recovery / Controlled Reindex v1`"])
    return render_markdown_report("PRD-046.0.7.2-HF3 CHROMA RECONCILIATION REPORT", lines)


def _strict_gate_report(snapshot: dict[str, Any], smoke: dict[str, Any], reconciliation: dict[str, Any]) -> str:
    lines = [
        "## Status",
        f"- final_status: `{snapshot.get('final_status')}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "",
        "## Runtime",
        f"- /api/status: `{_endpoint_status(smoke, '/api/status')}`",
        f"- /api/registry: `{_endpoint_status(smoke, '/api/registry')}`",
        f"- /api/registry/: `{_endpoint_status(smoke, '/api/registry/')}`",
        f"- /api/dashboard: `{_endpoint_status(smoke, '/api/dashboard')}`",
        f"- /api/dashboard/: `{_endpoint_status(smoke, '/api/dashboard/')}`",
        "",
        "## Strict Chroma Gate",
        f"- strict_chroma_count_passed: `{reconciliation.get('strict_gate_passed')}`",
        f"- reconciliation_status: `{reconciliation.get('reconciliation_status')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF3 STRICT GATE REPORT", lines)


def _next_prd_report(snapshot: dict[str, Any]) -> str:
    final_status = str(snapshot.get("final_status") or "failed")
    if final_status == "passed":
        next_prd = "PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD"
    elif final_status == "done_with_chroma_count_blocker":
        next_prd = "PRD-046.0.7.2-HF4 - Chroma Count Recovery / Controlled Reindex v1"
    elif final_status == "done_with_admin_api_blocker":
        next_prd = "PRD-046.0.7.2-HF4 - Admin API Runtime Availability Recovery v1"
    else:
        next_prd = "PRD-046.0.7.2-HF4 - Admin Runtime/Schema Reconciliation v1"
    lines = [
        "## Recommendation",
        f"- next_prd: `{next_prd}`",
        f"- final_status: `{final_status}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF3 NEXT PRD RECOMMENDATION", lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    reports_dir = Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    apply_result_path = Path(args.apply_result)
    overlay_path = Path(args.overlay)
    review_queue_path = Path(args.review_queue)

    blocks_hash_before = sha256_file(blocks_path)
    registry_hash_before = sha256_file(registry_path)

    live = run_admin_live_smoke(
        admin_base_url=str(args.admin_base_url),
        source_prd=str(args.source_prd),
        expected_source_id=str(args.source_id),
        expected_blocks_total=int(args.expected_blocks),
        require_admin_api=bool(args.require_admin_api),
        try_start_server=bool(args.try_start_server),
        startup_timeout_sec=int(args.startup_timeout_sec),
        http_timeout_sec=float(args.http_timeout_sec),
        repo_root=REPO_ROOT,
    )
    smoke = live["smoke"]

    historical_chroma_count, historical_proof_path = _load_historical_chroma_count()
    direct_chroma_count, direct_count_error = _read_direct_chroma_count()

    reconciliation = build_chroma_count_reconciliation(
        source_prd=str(args.source_prd),
        admin_base_url=str(args.admin_base_url),
        smoke=smoke,
        expected_source_id=str(args.source_id),
        expected_blocks=int(args.expected_blocks),
        direct_chroma_count=direct_chroma_count,
        historical_chroma_count=historical_chroma_count,
        historical_proof_path=historical_proof_path,
    )
    if direct_count_error:
        warnings = list(reconciliation.get("warnings") or [])
        warnings.append(direct_count_error)
        reconciliation["warnings"] = sorted(set(warnings))

    existing_warnings = [item for item in (smoke.get("warnings") or []) if item != "dashboard_chroma_count_mismatch_accepted_with_local_proof" and not str(item).startswith("local_chroma_count_proof:")]
    smoke["warnings"] = sorted(set(existing_warnings + list(reconciliation.get("warnings") or [])))

    existing_issues = list(smoke.get("issues") or [])
    smoke["issues"] = sorted(set(existing_issues + list(reconciliation.get("issues") or [])))
    smoke["strict_chroma_count_passed"] = bool(reconciliation.get("strict_gate_passed"))
    smoke["direct_chroma_count"] = direct_chroma_count
    smoke["historical_chroma_count"] = historical_chroma_count
    smoke["historical_proof_path"] = historical_proof_path
    smoke["chroma_reconciliation_status"] = reconciliation.get("reconciliation_status")

    if not bool(reconciliation.get("strict_gate_passed")):
        smoke["admin_consistency_passed"] = False
        if "dashboard_chroma_count_mismatch" in (reconciliation.get("issues") or []):
            smoke["admin_runtime_status"] = "blocked_chroma_count_mismatch"
        elif str(smoke.get("admin_runtime_status") or "") == "passed":
            smoke["admin_runtime_status"] = "failed_schema_validation"

    payload_shape = _build_payload_shape_sanitized_hf3(smoke)

    write_json(out_dir / "admin_live_smoke_hf3.json", smoke)
    write_json(out_dir / "chroma_count_reconciliation.json", reconciliation)
    write_json(out_dir / "admin_payload_shape_sanitized_hf3.json", payload_shape)

    blocks_payload = read_json(blocks_path)
    registry_payload = read_json(registry_path)
    apply_result_payload = read_json(apply_result_path)
    overlay_payload = read_json(overlay_path)
    review_queue_payload = read_json(review_queue_path)

    data_consistency = build_data_consistency_gate(
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        apply_result_payload=apply_result_payload if isinstance(apply_result_payload, dict) else {},
        expected_blocks_total=int(args.expected_blocks),
        expected_source_id=str(args.source_id),
    )
    apply_route_consistency = build_apply_route_consistency(
        blocks_payload=blocks_payload,
        apply_result_payload=apply_result_payload if isinstance(apply_result_payload, dict) else {},
        decisions_overlay_payload=overlay_payload if isinstance(overlay_payload, dict) else {},
        review_queue_payload=review_queue_payload if isinstance(review_queue_payload, dict) else {},
    )
    retrieval_quality = build_retrieval_quality_smoke(
        blocks_payload=blocks_payload,
        expected_source_id=str(args.source_id),
    )
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

    snapshot = build_quality_gate_snapshot(
        source_prd=str(args.source_prd),
        data_consistency=data_consistency,
        apply_route_consistency=apply_route_consistency,
        retrieval_quality=retrieval_quality,
        writer_policy=writer_policy,
        admin_runtime=smoke,
        no_mutation_proof=no_mutation,
    )
    snapshot["schema_version"] = "strict_quality_gate_hf3_v1"
    snapshot["strict_chroma_count_passed"] = bool(reconciliation.get("strict_gate_passed"))
    write_json(out_dir / "strict_quality_gate_hf3.json", snapshot)

    write_text(
        reports_dir / "PRD-046.0.7.2-HF3_IMPLEMENTATION_REPORT.md",
        _implementation_report(snapshot, smoke, reconciliation, no_mutation),
    )
    write_text(
        reports_dir / "PRD-046.0.7.2-HF3_CHROMA_RECONCILIATION_REPORT.md",
        _chroma_reconciliation_report(reconciliation),
    )
    write_text(
        reports_dir / "PRD-046.0.7.2-HF3_STRICT_GATE_REPORT.md",
        _strict_gate_report(snapshot, smoke, reconciliation),
    )
    write_text(
        reports_dir / "PRD-046.0.7.2-HF3_NEXT_PRD_RECOMMENDATION.md",
        _next_prd_report(snapshot),
    )

    return {
        "status": str(snapshot.get("final_status") or "failed"),
        "admin_live_smoke_hf3": smoke,
        "chroma_count_reconciliation": reconciliation,
        "strict_quality_gate_hf3": snapshot,
        "no_mutation_proof": no_mutation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.7.2-HF3 strict dashboard/chroma reconciliation runner.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2-HF3")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--require-admin-api", dest="require_admin_api", action="store_true", default=True)
    parser.add_argument("--no-require-admin-api", dest="require_admin_api", action="store_false")
    parser.add_argument("--try-start-server", action="store_true", default=False)
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--http-timeout-sec", type=float, default=20.0)
    parser.add_argument("--source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument("--apply-result", default="TO_DO_LIST/logs/PRD-046.0.7.1/apply_result.json")
    parser.add_argument("--overlay", default="TO_DO_LIST/logs/PRD-046.0.9.3/architect_auto_decisions_overlay.json")
    parser.add_argument("--review-queue", default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json")
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.7.2-HF3")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    args = parser.parse_args()

    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    status = str(result.get("status") or "failed")
    if status in {
        "passed",
        "done_with_admin_api_blocker",
        "done_with_admin_launch_blocker",
        "done_with_admin_schema_blocker",
        "done_with_chroma_count_blocker",
    }:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
