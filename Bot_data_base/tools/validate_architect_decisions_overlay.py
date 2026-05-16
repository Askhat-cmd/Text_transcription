from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.architect_review_pass import (
    build_no_mutation_proof,
    read_json,
    read_optional_chroma_count,
    render_architect_validation_markdown,
    sanitize_runtime_log_lines,
    sha256_file,
    validate_architect_decisions_overlay,
    write_json,
    write_text,
)
from review.post_reprocess_review_decisions import find_fresh_review_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate architect decisions overlay for aligned post-reprocess queue.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument(
        "--decisions",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_decisions_overlay.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--source-prd", default="PRD-046.0.9.2")
    parser.add_argument("--expected-queue-count", type=int, default=87)
    parser.add_argument(
        "--out",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_decisions_validation.json",
    )
    parser.add_argument(
        "--out-md",
        default="TO_DO_LIST/reports/PRD-046.0.9.2_DECISIONS_VALIDATION_REPORT.md",
    )
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    parser.add_argument(
        "--no-mutation-out",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/no_mutation_proof.json",
    )
    args = parser.parse_args()

    queue_path = find_fresh_review_queue(Path(args.review_queue))
    decisions_path = Path(args.decisions)
    blocks_path = Path(args.blocks)
    out_path = Path(args.out)
    out_md = Path(args.out_md)
    registry_path = Path(args.registry)
    chroma_snapshot_path = Path(args.chroma_snapshot)
    no_mutation_out = Path(args.no_mutation_out)

    if not queue_path.exists() or not decisions_path.exists() or not blocks_path.exists():
        payload = {
            "schema_version": "architect_review_decisions_validation_v1",
            "source_prd": args.source_prd,
            "valid": False,
            "errors": ["queue_or_decisions_or_blocks_missing"],
            "warnings": [],
            "coverage": {
                "queue_items_count": 0,
                "decisions_count": 0,
                "unique_review_item_ids_count": 0,
                "remaining_items_count": 0,
                "coverage_percent": 0.0,
            },
            "ready_for_architect_review": False,
            "apply_ready": False,
            "invalid_decision_values": [],
            "forbidden_key_hits": [],
            "secret_like_hits": [],
            "duplicate_review_item_ids": [],
            "unknown_review_item_ids": [],
            "block_id_mismatches": [],
            "authority_field_mutation_attempts": [],
        }
        write_json(out_path, payload)
        write_text(out_md, render_architect_validation_markdown(payload, source_prd=str(args.source_prd)))
        print(json.dumps({"ok": False, "reason": "queue_or_decisions_or_blocks_missing"}, ensure_ascii=False, indent=2))
        return 2

    queue_payload = read_json(queue_path)
    decisions_payload = read_json(decisions_path)
    blocks_payload = read_json(blocks_path)

    if not isinstance(queue_payload, dict):
        raise RuntimeError("review_queue_must_be_object")
    if not isinstance(decisions_payload, dict):
        raise RuntimeError("decisions_payload_must_be_object")

    validation = validate_architect_decisions_overlay(
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        blocks_payload=blocks_payload,
        source_prd=str(args.source_prd),
    )

    expected_queue_count = int(args.expected_queue_count)
    queue_items_count = int((validation.get("coverage") or {}).get("queue_items_count") or 0)
    if expected_queue_count >= 0 and queue_items_count != expected_queue_count:
        validation["valid"] = False
        validation["errors"] = sorted(set(list(validation.get("errors") or []) + ["queue_items_count_mismatch_expected"]))

    write_json(out_path, validation)
    write_text(out_md, render_architect_validation_markdown(validation, source_prd=str(args.source_prd)))

    chroma_count = read_optional_chroma_count(chroma_snapshot_path)
    no_mutation = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        decisions_overlay_path=decisions_path,
        blocks_hash_before=sha256_file(blocks_path),
        registry_hash_before=sha256_file(registry_path) if registry_path.exists() else "",
        chroma_count_before=chroma_count,
        chroma_count_after=chroma_count,
    )
    write_json(no_mutation_out, no_mutation)

    coverage = validation.get("coverage") if isinstance(validation.get("coverage"), dict) else {}
    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"queue_path={queue_path.as_posix()}",
            f"decisions_path={decisions_path.as_posix()}",
            f"queue_items_count={coverage.get('queue_items_count')}",
            f"expected_queue_count={expected_queue_count}",
            f"decisions_count={coverage.get('decisions_count')}",
            f"unique_review_item_ids_count={coverage.get('unique_review_item_ids_count')}",
            f"remaining_items_count={coverage.get('remaining_items_count')}",
            f"coverage_percent={coverage.get('coverage_percent')}",
            f"ready_for_architect_review={validation.get('ready_for_architect_review')}",
            f"apply_ready={validation.get('apply_ready')}",
            f"valid={validation.get('valid')}",
            f"errors_count={len(validation.get('errors') or [])}",
            f"warnings_count={len(validation.get('warnings') or [])}",
            f"production_apply_performed={no_mutation.get('production_apply_performed')}",
            f"chroma_reindex_performed={no_mutation.get('chroma_reindex_performed')}",
        ]
    )
    write_text(no_mutation_out.parent / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if bool(validation.get("valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
