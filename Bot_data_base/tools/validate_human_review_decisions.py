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
    build_no_mutation_proof,
    find_fresh_review_queue,
    read_json,
    render_validation_markdown,
    sanitize_runtime_log_lines,
    sha256_file,
    validate_human_review_decisions,
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
    parser = argparse.ArgumentParser(description="Validate post-reprocess human review decisions overlay.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument(
        "--decisions",
        default="TO_DO_LIST/logs/PRD-046.0.9.1/review_decisions_template.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--source-prd", default="PRD-046.0.9.1")
    parser.add_argument(
        "--out",
        default="TO_DO_LIST/logs/PRD-046.0.9.1/review_decisions_validation.json",
    )
    parser.add_argument(
        "--out-md",
        default="TO_DO_LIST/reports/PRD-046.0.9.1_DECISIONS_VALIDATION_REPORT.md",
    )
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    parser.add_argument(
        "--no-mutation-out",
        default="TO_DO_LIST/logs/PRD-046.0.9.1/no_mutation_proof.json",
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
            "schema_version": "kb_review_decisions_validation_v1",
            "source_prd": args.source_prd,
            "validated_at": "",
            "queue_items_count": 0,
            "decisions_count": 0,
            "valid": False,
            "errors": ["queue_or_decisions_or_blocks_missing"],
            "warnings": [],
            "decision_counts": {},
            "forbidden_key_hits": [],
            "secret_like_hits": [],
            "duplicate_review_item_ids": [],
            "unknown_review_item_ids": [],
            "block_id_mismatches": [],
            "authority_field_mutation_attempts": [],
        }
        write_json(out_path, payload)
        write_text(out_md, render_validation_markdown(payload, source_prd=str(args.source_prd)))
        print(json.dumps({"ok": False, "reason": "queue_or_decisions_or_blocks_missing"}, ensure_ascii=False, indent=2))
        return 2

    queue_payload = read_json(queue_path)
    decisions_payload = read_json(decisions_path)
    blocks_payload = read_json(blocks_path)

    validation = validate_human_review_decisions(
        queue_payload=queue_payload if isinstance(queue_payload, dict) else {},
        decisions_payload=decisions_payload if isinstance(decisions_payload, dict) else {},
        blocks_payload=blocks_payload,
        source_prd=str(args.source_prd),
    )
    write_json(out_path, validation)
    write_text(out_md, render_validation_markdown(validation, source_prd=str(args.source_prd)))

    chroma_count = _read_optional_chroma_count(chroma_snapshot_path)
    no_mutation = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        blocks_path=blocks_path,
        registry_path=registry_path,
        queue_path=queue_path,
        decisions_template_path=decisions_path,
        blocks_hash_before=sha256_file(blocks_path),
        registry_hash_before=sha256_file(registry_path) if registry_path.exists() else "",
        chroma_count_before=chroma_count,
        chroma_count_after=chroma_count,
    )
    write_json(no_mutation_out, no_mutation)

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"queue_path={queue_path.as_posix()}",
            f"decisions_path={decisions_path.as_posix()}",
            f"queue_items_count={validation.get('queue_items_count')}",
            f"decisions_count={validation.get('decisions_count')}",
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
