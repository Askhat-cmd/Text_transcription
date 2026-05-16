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

from review.post_apply_quality_gate import (  # noqa: E402
    build_admin_api_runtime_smoke,
    build_apply_route_consistency,
    build_data_consistency_gate,
    build_no_mutation_proof,
    build_quality_gate_snapshot,
    build_retrieval_quality_smoke,
    build_runtime_log_lines,
    build_writer_kb_policy_smoke,
    read_json,
    render_markdown_report,
    sha256_file,
    write_json,
    write_text,
)


def _quality_gate_markdown(snapshot: dict[str, Any]) -> str:
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
    return render_markdown_report("PRD-046.0.7.2 QUALITY GATE REPORT", lines)


def _implementation_markdown(snapshot: dict[str, Any], no_mutation: dict[str, Any]) -> str:
    lines = [
        "## Status",
        "- implementation: done",
        f"- final_status: `{snapshot.get('final_status')}`",
        f"- quality_gate_passed: `{snapshot.get('quality_gate_passed')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
        "- production_apply_performed: `false`",
        "- chroma_reindex_performed: `false`",
        "- provider_called: `false`",
        "",
        "## No Mutation",
        f"- all_blocks_merged_mutated: `{no_mutation.get('all_blocks_merged_mutated')}`",
        f"- registry_mutated: `{no_mutation.get('registry_mutated')}`",
        f"- all_blocks_hash_before: `{no_mutation.get('all_blocks_merged_hash_before')}`",
        f"- all_blocks_hash_after: `{no_mutation.get('all_blocks_merged_hash_after')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2 IMPLEMENTATION REPORT", lines)


def _next_prd_markdown(snapshot: dict[str, Any]) -> str:
    if bool(snapshot.get("quality_gate_passed")):
        recommendation = "Diagnostic Center v1 Design / Readiness PRD"
    else:
        recommendation = "PRD-046.0.7.2-HF1 — Admin Runtime Gate Fix / Live Smoke v1"
    lines = [
        "## Recommendation",
        f"- next_prd: `{recommendation}`",
        f"- admin_runtime_status: `{snapshot.get('admin_runtime_status')}`",
        f"- diagnostic_center_ready: `{snapshot.get('diagnostic_center_ready')}`",
    ]
    return render_markdown_report("PRD-046.0.7.2 NEXT PRD RECOMMENDATION", lines)


def run_quality_gate(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    reports_dir = Path(args.reports_dir)

    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    apply_result_path = Path(args.apply_result)
    overlay_path = Path(args.overlay)
    review_queue_path = Path(args.review_queue)

    blocks_hash_before = sha256_file(blocks_path)
    registry_hash_before = sha256_file(registry_path)

    blocks_payload = read_json(blocks_path)
    registry_payload = read_json(registry_path)
    apply_result_payload = read_json(apply_result_path)
    overlay_payload = read_json(overlay_path)
    review_queue_payload = read_json(review_queue_path)

    data_consistency = build_data_consistency_gate(
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        apply_result_payload=apply_result_payload if isinstance(apply_result_payload, dict) else {},
        expected_blocks_total=int(args.expected_blocks_total),
        expected_source_id=str(args.expected_source_id),
    )
    write_json(out_dir / "data_consistency_gate.json", data_consistency)

    apply_route_consistency = build_apply_route_consistency(
        blocks_payload=blocks_payload,
        apply_result_payload=apply_result_payload if isinstance(apply_result_payload, dict) else {},
        decisions_overlay_payload=overlay_payload if isinstance(overlay_payload, dict) else {},
        review_queue_payload=review_queue_payload if isinstance(review_queue_payload, dict) else {},
    )
    write_json(out_dir / "apply_route_consistency.json", apply_route_consistency)

    retrieval_quality = build_retrieval_quality_smoke(
        blocks_payload=blocks_payload,
        expected_source_id=str(args.expected_source_id),
    )
    write_json(out_dir / "retrieval_quality_smoke.json", retrieval_quality)

    writer_policy = build_writer_kb_policy_smoke(blocks_payload=blocks_payload)
    write_json(out_dir / "writer_kb_policy_smoke.json", writer_policy)

    admin_runtime = build_admin_api_runtime_smoke(
        admin_base_url=str(args.admin_base_url),
        expected_source_id=str(args.expected_source_id),
        expected_blocks_total=int(args.expected_blocks_total),
        allow_offline_admin_checks=bool(args.allow_offline_admin_checks),
        require_admin_api=bool(args.require_admin_api),
    )
    write_json(out_dir / "admin_api_runtime_smoke.json", admin_runtime)

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
        admin_runtime=admin_runtime,
        no_mutation_proof=no_mutation,
    )
    write_json(out_dir / "post_apply_quality_gate.json", snapshot)

    runtime_lines = build_runtime_log_lines(
        {
            "source_prd": args.source_prd,
            "final_status": snapshot.get("final_status"),
            "quality_gate_passed": snapshot.get("quality_gate_passed"),
            "admin_runtime_status": snapshot.get("admin_runtime_status"),
            "diagnostic_center_ready": snapshot.get("diagnostic_center_ready"),
            "data_consistency_passed": snapshot.get("data_consistency_passed"),
            "apply_route_consistency_passed": snapshot.get("apply_route_consistency_passed"),
            "retrieval_quality_passed": snapshot.get("retrieval_quality_passed"),
            "writer_kb_policy_passed": snapshot.get("writer_kb_policy_passed"),
            "admin_consistency_passed": snapshot.get("admin_consistency_passed"),
            "all_blocks_mutated": no_mutation.get("all_blocks_merged_mutated"),
            "registry_mutated": no_mutation.get("registry_mutated"),
        }
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    write_text(reports_dir / "PRD-046.0.7.2_QUALITY_GATE_REPORT.md", _quality_gate_markdown(snapshot))
    write_text(reports_dir / "PRD-046.0.7.2_IMPLEMENTATION_REPORT.md", _implementation_markdown(snapshot, no_mutation))
    write_text(reports_dir / "PRD-046.0.7.2_NEXT_PRD_RECOMMENDATION.md", _next_prd_markdown(snapshot))

    return {
        "status": str(snapshot.get("final_status") or "failed"),
        "snapshot": snapshot,
        "data_consistency": data_consistency,
        "apply_route_consistency": apply_route_consistency,
        "retrieval_quality": retrieval_quality,
        "writer_policy": writer_policy,
        "admin_runtime": admin_runtime,
        "no_mutation_proof": no_mutation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-046.0.7.2 post-apply retrieval/admin quality gate.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2")
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument("--apply-result", default="TO_DO_LIST/logs/PRD-046.0.7.1/apply_result.json")
    parser.add_argument("--overlay", default="TO_DO_LIST/logs/PRD-046.0.9.3/architect_auto_decisions_overlay.json")
    parser.add_argument("--review-queue", default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks-total", type=int, default=247)
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-admin-api", dest="require_admin_api", action="store_true", default=True)
    parser.add_argument("--no-require-admin-api", dest="require_admin_api", action="store_false")
    parser.add_argument("--allow-offline-admin-checks", action="store_true", default=False)
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.7.2")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    args = parser.parse_args()

    result = run_quality_gate(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    status = str(result.get("status") or "failed")
    if status == "passed":
        return 0
    if status == "done_with_admin_api_blocker":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
