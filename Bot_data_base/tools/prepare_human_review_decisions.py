from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.post_reprocess_review_decisions import (
    build_block_index,
    build_no_mutation_proof,
    build_review_decisions_example,
    build_review_decisions_summary,
    build_review_decisions_template,
    build_review_source_manifest,
    build_review_workbench,
    find_fresh_review_queue,
    read_json,
    sanitize_runtime_log_lines,
    sha256_file,
    write_json,
    write_text,
)


def _read_optional_chroma_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("dashboard_chroma_count", "registry_chroma_count", "chroma_count", "chroma_count_after", "count"):
        value = payload.get(key)
        try:
            if value is not None:
                return int(value)
        except Exception:
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare human review decisions artifacts for post-reprocess queue.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--source-prd", default="PRD-046.0.9.1")
    parser.add_argument("--expected-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.9.1")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    queue_path = find_fresh_review_queue(Path(args.review_queue))
    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    chroma_snapshot_path = Path(args.chroma_snapshot)

    if not blocks_path.exists():
        raise FileNotFoundError(f"blocks_file_missing:{blocks_path.as_posix()}")

    queue_payload = read_json(queue_path)
    if not isinstance(queue_payload, dict):
        raise RuntimeError("review_queue_must_be_object")

    blocks_payload = read_json(blocks_path)
    block_index = build_block_index(blocks_payload)

    manifest = build_review_source_manifest(
        queue_payload=queue_payload,
        queue_path=queue_path,
        blocks_path=blocks_path,
        source_prd=str(args.source_prd),
        expected_source_prd=str(args.expected_source_prd),
        block_index=block_index,
        registry_path=registry_path,
        chroma_snapshot_path=chroma_snapshot_path,
    )
    write_json(out_dir / "review_source_manifest.json", manifest)

    workbench = build_review_workbench(
        queue_payload=queue_payload,
        block_index=block_index,
        source_prd=str(args.source_prd),
        queue_source_prd=str(queue_payload.get("source_prd") or ""),
    )
    write_text(out_dir / "review_workbench.md", workbench)

    template = build_review_decisions_template(
        source_prd=str(args.source_prd),
        source_review_queue_prd=str(queue_payload.get("source_prd") or ""),
        review_queue_hash=sha256_file(queue_path),
        blocks_hash_before=sha256_file(blocks_path),
    )
    write_json(out_dir / "review_decisions_template.json", template)

    example = build_review_decisions_example(queue_payload=queue_payload, source_prd=str(args.source_prd))
    write_json(out_dir / "review_decisions.example.json", example)

    summary = build_review_decisions_summary(queue_payload=queue_payload, manifest=manifest, template=template)
    write_json(out_dir / "review_decisions_summary.json", summary)

    chroma_count = _read_optional_chroma_count(chroma_snapshot_path)
    no_mutation_proof = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        blocks_path=blocks_path,
        registry_path=registry_path,
        queue_path=queue_path,
        decisions_template_path=out_dir / "review_decisions_template.json",
        blocks_hash_before=manifest.get("blocks_hash_before") or "",
        registry_hash_before=manifest.get("registry_hash_before") or "",
        chroma_count_before=chroma_count,
        chroma_count_after=chroma_count,
    )
    write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"queue_path={queue_path.as_posix()}",
            f"queue_items_count={summary.get('queue_items_count')}",
            f"queue_source_prd={queue_payload.get('source_prd')}",
            f"expected_source_prd={args.expected_source_prd}",
            f"queue_source_prd_match={manifest.get('source_review_queue_prd_match')}",
            f"queue_block_ids_missing_in_blocks_count={manifest.get('queue_block_ids_missing_in_blocks_count')}",
            f"production_apply_performed={no_mutation_proof.get('production_apply_performed')}",
            f"chroma_reindex_performed={no_mutation_proof.get('chroma_reindex_performed')}",
        ]
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "source_prd": args.source_prd,
                "queue_path": queue_path.as_posix(),
                "queue_items_count": summary.get("queue_items_count"),
                "queue_block_ids_missing_in_blocks_count": manifest.get("queue_block_ids_missing_in_blocks_count"),
                "out_dir": out_dir.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
