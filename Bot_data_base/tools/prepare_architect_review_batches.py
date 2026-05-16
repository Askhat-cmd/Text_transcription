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
    build_architect_decisions_template,
    build_architect_review_items,
    build_no_mutation_proof,
    create_architect_batches,
    queue_alignment_summary,
    read_json,
    read_optional_chroma_count,
    render_batches_report,
    sanitize_runtime_log_lines,
    sha256_file,
    write_json,
    write_text,
)
from review.post_reprocess_review_decisions import find_fresh_review_queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare architect semantic review batches from aligned post-reprocess queue.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--source-prd", default="PRD-046.0.9.2")
    parser.add_argument("--expected-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--expected-queue-count", type=int, default=87)
    parser.add_argument("--batch-size", type=int, default=11)
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.9.2")
    parser.add_argument(
        "--out-md",
        default="TO_DO_LIST/reports/PRD-046.0.9.2_ARCHITECT_REVIEW_BATCHES_REPORT.md",
    )
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    args = parser.parse_args()

    queue_path = find_fresh_review_queue(Path(args.review_queue))
    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    chroma_snapshot_path = Path(args.chroma_snapshot)
    out_dir = Path(args.out_dir)
    out_md = Path(args.out_md)

    if not queue_path.exists() or not blocks_path.exists():
        raise FileNotFoundError("review_queue_or_blocks_missing")

    queue_payload = read_json(queue_path)
    blocks_payload = read_json(blocks_path)
    if not isinstance(queue_payload, dict):
        raise RuntimeError("review_queue_must_be_object")

    source_queue_prd = str(queue_payload.get("source_prd") or "")
    expected_source_prd = str(args.expected_source_prd)

    alignment = queue_alignment_summary(queue_payload, blocks_payload)
    items = build_architect_review_items(queue_payload=queue_payload, blocks_payload=blocks_payload)

    index_payload = create_architect_batches(
        items=items,
        source_prd=str(args.source_prd),
        queue_source_prd=source_queue_prd,
        out_dir=out_dir,
        batch_size=int(args.batch_size),
    )

    review_queue_hash = sha256_file(queue_path)
    blocks_hash_before = sha256_file(blocks_path)
    template = build_architect_decisions_template(
        source_prd=str(args.source_prd),
        queue_source_prd=source_queue_prd,
        review_queue_hash=review_queue_hash,
        blocks_hash_before=blocks_hash_before,
    )
    write_json(out_dir / "architect_decisions_template.json", template)
    write_json(out_dir / "architect_decisions_overlay.json", template)

    chroma_count = read_optional_chroma_count(chroma_snapshot_path)
    registry_hash_before = sha256_file(registry_path) if registry_path.exists() else ""
    no_mutation = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        decisions_overlay_path=out_dir / "architect_decisions_overlay.json",
        blocks_hash_before=blocks_hash_before,
        registry_hash_before=registry_hash_before,
        chroma_count_before=chroma_count,
        chroma_count_after=chroma_count,
    )
    write_json(out_dir / "no_mutation_proof.json", no_mutation)

    report_text = render_batches_report(index_payload=index_payload, alignment=alignment, source_prd=str(args.source_prd))
    write_text(out_md, report_text)

    queue_items_count = int(alignment.get("queue_items_count") or 0)
    queue_missing = int(alignment.get("queue_block_ids_missing") or 0)
    expected_queue_count = int(args.expected_queue_count)
    forbidden_hits = index_payload.get("forbidden_batch_keys_detected") or []

    source_prd_match = source_queue_prd == expected_source_prd
    queue_count_match = expected_queue_count < 0 or queue_items_count == expected_queue_count

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"review_queue={queue_path.as_posix()}",
            f"review_queue_source_prd={source_queue_prd}",
            f"expected_source_prd={expected_source_prd}",
            f"source_prd_match={source_prd_match}",
            f"queue_items_count={queue_items_count}",
            f"expected_queue_count={expected_queue_count}",
            f"queue_count_match={queue_count_match}",
            f"queue_block_ids_missing={queue_missing}",
            f"batches_count={index_payload.get('batches_count')}",
            f"batch_size_requested={index_payload.get('batch_size_requested')}",
            f"forbidden_batch_keys_detected_count={len(forbidden_hits)}",
            f"ready_for_architect_review={template.get('ready_for_architect_review')}",
            f"apply_ready={template.get('apply_ready')}",
            f"production_apply_performed={no_mutation.get('production_apply_performed')}",
            f"chroma_reindex_performed={no_mutation.get('chroma_reindex_performed')}",
        ]
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    ok = bool(source_prd_match and queue_count_match and queue_missing == 0 and len(forbidden_hits) == 0)
    payload = {
        "ok": ok,
        "source_prd": args.source_prd,
        "out_dir": out_dir.as_posix(),
        "queue_items_count": queue_items_count,
        "expected_queue_count": expected_queue_count,
        "queue_count_match": queue_count_match,
        "source_prd_match": source_prd_match,
        "queue_block_ids_missing": queue_missing,
        "batches_count": index_payload.get("batches_count"),
        "forbidden_batch_keys_detected": forbidden_hits,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
