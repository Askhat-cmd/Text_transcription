from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.blocks_snapshot_alignment import (
    build_alignment_audit,
    read_json,
    render_alignment_report,
    sanitize_runtime_log_lines,
    write_json,
    write_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit blocks snapshot alignment against fresh review queue.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    parser.add_argument("--expected-blocks-total", type=int, default=247)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--source-prd", default="PRD-046.0.9.1-HF1")
    parser.add_argument(
        "--scan-root",
        action="append",
        default=[
            "TO_DO_LIST/logs/PRD-046.0.8.1",
            "TO_DO_LIST/logs/PRD-046.0.9",
            "TO_DO_LIST/logs/PRD-046.0.9-RUN1",
            "Bot_data_base/data/backups",
            "Bot_data_base/data/processed/backups",
        ],
    )
    parser.add_argument(
        "--out",
        default="TO_DO_LIST/logs/PRD-046.0.9.1-HF1/blocks_alignment_audit.json",
    )
    parser.add_argument(
        "--out-md",
        default="TO_DO_LIST/reports/PRD-046.0.9.1-HF1_BLOCKS_ALIGNMENT_AUDIT_REPORT.md",
    )
    args = parser.parse_args()

    queue_path = Path(args.review_queue)
    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    chroma_snapshot_path = Path(args.chroma_snapshot)
    out_path = Path(args.out)
    out_md = Path(args.out_md)

    if not queue_path.exists() or not blocks_path.exists() or not registry_path.exists():
        payload = {
            "schema_version": "blocks_snapshot_alignment_audit_v1",
            "source_prd": args.source_prd,
            "generated_at": "",
            "status": "blocked_missing_inputs",
            "errors": ["queue_or_blocks_or_registry_missing"],
        }
        write_json(out_path, payload)
        write_text(out_md, render_alignment_report(payload, source_prd=str(args.source_prd)))
        print(json.dumps({"ok": False, "reason": "queue_or_blocks_or_registry_missing"}, ensure_ascii=False, indent=2))
        return 2

    queue_payload = read_json(queue_path)
    blocks_payload = read_json(blocks_path)
    registry_payload = read_json(registry_path)

    scan_roots = [Path(item) for item in (args.scan_root or [])]

    audit = build_alignment_audit(
        queue_payload=queue_payload if isinstance(queue_payload, dict) else {},
        blocks_payload=blocks_payload,
        registry_payload=registry_payload,
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        expected_blocks_total=max(1, int(args.expected_blocks_total)),
        expected_source_id=str(args.expected_source_id),
        scan_roots=scan_roots,
        chroma_snapshot_path=chroma_snapshot_path,
        source_prd=str(args.source_prd),
    )

    write_json(out_path, audit)
    write_text(out_md, render_alignment_report(audit, source_prd=str(args.source_prd)))

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"status={audit.get('status')}",
            f"blocks_total={audit.get('blocks_total')}",
            f"expected_blocks_total={audit.get('expected_blocks_total')}",
            f"queue_items_count={audit.get('queue_items_count')}",
            f"queue_block_ids_present_count={audit.get('queue_block_ids_present_count')}",
            f"queue_block_ids_missing_count={audit.get('queue_block_ids_missing_count')}",
            f"authoritative_candidates_found={audit.get('authoritative_candidates_found')}",
        ]
    )
    write_text(out_path.parent / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
