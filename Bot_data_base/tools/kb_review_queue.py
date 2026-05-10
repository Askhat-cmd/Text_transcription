from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.review_queue_builder import build_review_queue, discover_input_file
from review.review_sanitizer import assert_review_artifact_is_sanitized


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_template(queue_payload: dict, source_prd: str) -> dict:
    return {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "queue_schema_version": queue_payload.get("schema_version"),
        "queue_generated_at": queue_payload.get("generated_at"),
        "decisions": [],
    }


def _write_markdown_report(path: Path, queue_payload: dict, degraded_reason: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PRD-046.0.7 REVIEW QUEUE REPORT", ""]
    if degraded_reason:
        lines.extend(
            [
                "## Status",
                "- mode: degraded",
                f"- reason: {degraded_reason}",
            ]
        )
    else:
        lines.extend(
            [
                "## Status",
                "- mode: normal",
                f"- source_mutated: {queue_payload.get('source_mutated')}",
                f"- total_blocks_scanned: {queue_payload.get('total_blocks_scanned')}",
                f"- review_items_count: {queue_payload.get('review_items_count')}",
            ]
        )
        lines.extend(
            [
                "",
                "## Priority Counts",
                f"- P0: {queue_payload.get('priority_counts', {}).get('P0', 0)}",
                f"- P1: {queue_payload.get('priority_counts', {}).get('P1', 0)}",
                f"- P2: {queue_payload.get('priority_counts', {}).get('P2', 0)}",
                "",
                "## Recommended Actions",
                f"- approve: {queue_payload.get('recommended_action_counts', {}).get('approve', 0)}",
                f"- reject: {queue_payload.get('recommended_action_counts', {}).get('reject', 0)}",
                f"- needs_edit: {queue_payload.get('recommended_action_counts', {}).get('needs_edit', 0)}",
                f"- split_merge_review: {queue_payload.get('recommended_action_counts', {}).get('split_merge_review', 0)}",
                f"- defer: {queue_payload.get('recommended_action_counts', {}).get('defer', 0)}",
                "",
                "## Input Integrity",
                f"- input_file: {queue_payload.get('input_file')}",
                f"- input_file_sha256_before: {queue_payload.get('input_file_sha256_before')}",
                f"- input_file_sha256_after: {queue_payload.get('input_file_sha256_after')}",
            ]
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sanitized human-review queue from processed KB blocks.")
    parser.add_argument("--input-json", default="")
    parser.add_argument("--output-json", default="TO_DO_LIST/logs/PRD-046.0.7/review_queue.json")
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7_REVIEW_QUEUE_REPORT.md",
    )
    parser.add_argument(
        "--template-json",
        default="TO_DO_LIST/logs/PRD-046.0.7/review_decisions_template.json",
    )
    parser.add_argument("--max-items", type=int, default=200)
    parser.add_argument("--source-prd", default="PRD-046.0.7")
    args = parser.parse_args()

    explicit = Path(args.input_json) if str(args.input_json or "").strip() else None
    input_path = discover_input_file(explicit)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    template_json = Path(args.template_json)

    if input_path is None:
        degraded_payload = {
            "schema_version": "kb_review_queue_v1",
            "source_prd": args.source_prd,
            "generated_at": _utc_now(),
            "input_file": str(explicit) if explicit else "",
            "source_mutated": False,
            "total_blocks_scanned": 0,
            "review_items_count": 0,
            "priority_counts": {"P0": 0, "P1": 0, "P2": 0},
            "recommended_action_counts": {
                "approve": 0,
                "reject": 0,
                "needs_edit": 0,
                "split_merge_review": 0,
                "defer": 0,
            },
            "items": [],
            "degraded_reason": "input_file_not_found",
        }
        _write_json(output_json, degraded_payload)
        _write_markdown_report(output_md, degraded_payload, degraded_reason="input_file_not_found")
        _write_json(template_json, _build_template(degraded_payload, source_prd=args.source_prd))
        print(json.dumps({"ok": False, "reason": "input_file_not_found"}, ensure_ascii=False, indent=2))
        return 2

    payload = build_review_queue(
        input_path=input_path,
        max_items=max(1, int(args.max_items)),
        source_prd=args.source_prd,
    )
    assert_review_artifact_is_sanitized(payload)
    _write_json(output_json, payload)
    _write_json(template_json, _build_template(payload, source_prd=args.source_prd))
    _write_markdown_report(output_md, payload)

    print(
        json.dumps(
            {
                "ok": True,
                "input_file": str(input_path.as_posix()),
                "total_blocks_scanned": payload.get("total_blocks_scanned"),
                "review_items_count": payload.get("review_items_count"),
                "output_json": str(output_json.as_posix()),
                "template_json": str(template_json.as_posix()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

