from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.admin_live_smoke import run_admin_live_smoke  # noqa: E402
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


def _endpoint_status(smoke: dict[str, Any], endpoint: str) -> str:
    payload = (smoke.get("api_checks") or {}).get(endpoint) if isinstance(smoke.get("api_checks"), dict) else None
    if not isinstance(payload, dict):
        return "n/a"
    code = payload.get("status_code")
    ok = bool(payload.get("ok"))
    return f"{code} / {'ok' if ok else 'fail'}"


def _admin_live_smoke_report(smoke: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "## Status",
        f"- admin_runtime_status: `{smoke.get('admin_runtime_status')}`",
        f"- admin_consistency_passed: `{smoke.get('admin_consistency_passed')}`",
        f"- server_launch_mode: `{manifest.get('server_launch_mode')}`",
        f"- server_started_by_hf1: `{manifest.get('server_started_by_hf1')}`",
        f"- readiness_passed: `{manifest.get('readiness_passed')}`",
        f"- readiness_poll_attempts: `{manifest.get('readiness_poll_attempts')}`",
        "",
        "## Endpoints",
        f"- /api/status: `{_endpoint_status(smoke, '/api/status')}`",
        f"- /api/registry: `{_endpoint_status(smoke, '/api/registry')}`",
        f"- /api/dashboard: `{_endpoint_status(smoke, '/api/dashboard')}`",
        f"- /api/dashboard/: `{_endpoint_status(smoke, '/api/dashboard/')}`",
        "",
        "## Expectations",
        f"- focus_source_id: `{smoke.get('focus_source_id')}`",
        f"- focus_blocks_count: `{smoke.get('focus_blocks_count')}`",
        f"- dashboard_blocks_count: `{smoke.get('dashboard_blocks_count')}`",
        f"- chroma_count: `{smoke.get('chroma_count')}`",
    ]
    issues = smoke.get("issues")
    if isinstance(issues, list) and issues:
        lines.extend(["", "## Issues", *[f"- `{item}`" for item in issues]])
    warnings = smoke.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.extend(["", "## Warnings", *[f"- `{item}`" for item in warnings]])
    return render_markdown_report("PRD-046.0.7.2-HF1 ADMIN LIVE SMOKE REPORT", lines)


def _quality_gate_report(snapshot: dict[str, Any]) -> str:
    lines = [
        "## Status",
        f"- final_status: `{snapshot.get('final_status')}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "",
        "## Gates",
        f"- data_consistency_passed: `{snapshot.get('data_consistency_passed')}`",
        f"- apply_route_consistency_passed: `{snapshot.get('apply_route_consistency_passed')}`",
        f"- retrieval_quality_passed: `{snapshot.get('retrieval_quality_passed')}`",
        f"- writer_kb_policy_passed: `{snapshot.get('writer_kb_policy_passed')}`",
        f"- admin_consistency_passed: `{snapshot.get('admin_consistency_passed')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF1 QUALITY GATE REPORT", lines)


def _implementation_report(
    *,
    snapshot: dict[str, Any],
    smoke: dict[str, Any],
    manifest: dict[str, Any],
    no_mutation: dict[str, Any],
) -> str:
    final_status = str(snapshot.get("final_status") or "failed")
    implementation_status = "done" if final_status == "passed" else final_status
    lines = [
        "## Status",
        f"- implementation: `{implementation_status}`",
        f"- final_status: `{final_status}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "",
        "## Admin runtime",
        f"- server_launch_mode: `{manifest.get('server_launch_mode')}`",
        f"- server_started_by_hf1: `{manifest.get('server_started_by_hf1')}`",
        f"- admin_base_url: `{smoke.get('admin_base_url')}`",
        f"- /api/status: `{_endpoint_status(smoke, '/api/status')}`",
        f"- /api/registry: `{_endpoint_status(smoke, '/api/registry')}`",
        f"- /api/dashboard: `{_endpoint_status(smoke, '/api/dashboard')}`",
        f"- /api/dashboard/: `{_endpoint_status(smoke, '/api/dashboard/')}`",
        f"- admin_runtime_status: `{smoke.get('admin_runtime_status')}`",
        "",
        "## Data expectations",
        f"- focus_source_id: `{smoke.get('focus_source_id')}`",
        f"- focus_blocks_count: `{smoke.get('focus_blocks_count')}`",
        f"- dashboard_blocks_count: `{smoke.get('dashboard_blocks_count')}`",
        f"- chroma_count: `{smoke.get('chroma_count')}`",
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
    return render_markdown_report("PRD-046.0.7.2-HF1 IMPLEMENTATION REPORT", lines)


def _next_prd_report(snapshot: dict[str, Any]) -> str:
    if bool(snapshot.get("quality_gate_passed")):
        next_prd = "PRD-046.1.0 - Diagnostic Center Readiness / Design Gate v1"
    else:
        next_prd = "PRD-046.0.7.2-HF2 - Admin API Launch/Schema Fix v1"
    lines = [
        "## Recommendation",
        f"- next_prd: `{next_prd}`",
        f"- final_status: `{snapshot.get('final_status')}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2-HF1 NEXT PRD RECOMMENDATION", lines)


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
    manifest = live["manifest"]
    smoke = live["smoke"]
    log_lines = live["sanitized_server_log_lines"]

    write_json(out_dir / "admin_launch_manifest.json", manifest)
    write_json(out_dir / "admin_live_smoke.json", smoke)
    if log_lines:
        log_text = "\n".join(log_lines) + "\n"
    else:
        log_text = "no_server_output_captured=true\n"
    write_text(out_dir / "sanitized_admin_server_logs.txt", log_text)

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
    snapshot["schema_version"] = "post_apply_quality_gate_after_live_admin_v1"
    write_json(out_dir / "post_apply_quality_gate_after_live_admin.json", snapshot)

    write_text(reports_dir / "PRD-046.0.7.2-HF1_ADMIN_LIVE_SMOKE_REPORT.md", _admin_live_smoke_report(smoke, manifest))
    write_text(reports_dir / "PRD-046.0.7.2-HF1_QUALITY_GATE_REPORT.md", _quality_gate_report(snapshot))
    write_text(
        reports_dir / "PRD-046.0.7.2-HF1_IMPLEMENTATION_REPORT.md",
        _implementation_report(snapshot=snapshot, smoke=smoke, manifest=manifest, no_mutation=no_mutation),
    )
    write_text(reports_dir / "PRD-046.0.7.2-HF1_NEXT_PRD_RECOMMENDATION.md", _next_prd_report(snapshot))

    return {
        "status": str(snapshot.get("final_status") or "failed"),
        "manifest": manifest,
        "admin_live_smoke": smoke,
        "snapshot": snapshot,
        "no_mutation_proof": no_mutation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-046.0.7.2-HF1 Admin Runtime Gate Fix / Live Smoke runner.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2-HF1")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-admin-api", dest="require_admin_api", action="store_true", default=True)
    parser.add_argument("--no-require-admin-api", dest="require_admin_api", action="store_false")
    parser.add_argument("--try-start-server", action="store_true", default=False)
    parser.add_argument("--no-start-server", dest="try_start_server", action="store_false")
    parser.add_argument("--startup-timeout-sec", type=int, default=30)
    parser.add_argument("--http-timeout-sec", type=float, default=12.0)
    parser.add_argument("--source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument("--apply-result", default="TO_DO_LIST/logs/PRD-046.0.7.1/apply_result.json")
    parser.add_argument("--overlay", default="TO_DO_LIST/logs/PRD-046.0.9.3/architect_auto_decisions_overlay.json")
    parser.add_argument("--review-queue", default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json")
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.7.2-HF1")
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
    }:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
