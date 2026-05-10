from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.review_decision_validator import validate_decisions_overlay
from review.review_sanitizer import assert_review_artifact_is_sanitized


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# PRD-046.0.7 REVIEW DECISIONS VALIDATION REPORT",
        "",
        "## Summary",
        f"- valid: {payload.get('valid')}",
        f"- queue_items_count: {payload.get('queue_items_count')}",
        f"- decisions_count: {payload.get('decisions_count')}",
        f"- errors_count: {len(payload.get('errors') or [])}",
        f"- warnings_count: {len(payload.get('warnings') or [])}",
        "",
        "## Errors",
    ]
    errors = payload.get("errors") or []
    if errors:
        for item in errors:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = payload.get("warnings") or []
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate review decisions overlay against review queue.")
    parser.add_argument("--queue-json", default="TO_DO_LIST/logs/PRD-046.0.7/review_queue.json")
    parser.add_argument(
        "--decisions-json",
        default="TO_DO_LIST/logs/PRD-046.0.7/review_decisions_template.json",
    )
    parser.add_argument(
        "--output-json",
        default="TO_DO_LIST/logs/PRD-046.0.7/review_decisions_validation.json",
    )
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7_REVIEW_DECISIONS_VALIDATION_REPORT.md",
    )
    parser.add_argument("--source-prd", default="PRD-046.0.7")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    queue_path = Path(args.queue_json)
    decisions_path = Path(args.decisions_json)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    if not queue_path.exists() or not decisions_path.exists():
        payload = {
            "schema_version": "kb_review_decisions_validation_v1",
            "source_prd": args.source_prd,
            "validated_at": "",
            "queue_items_count": 0,
            "decisions_count": 0,
            "valid": False,
            "errors": ["queue_or_decisions_file_missing"],
            "warnings": [],
            "forbidden_key_hits": [],
            "secret_like_hits": [],
            "unknown_review_item_ids": [],
            "decision_counts": {},
        }
        _write_json(output_json, payload)
        _write_markdown(output_md, payload)
        print(json.dumps({"ok": False, "reason": "queue_or_decisions_file_missing"}, ensure_ascii=False, indent=2))
        return 2

    queue_payload = _read_json(queue_path)
    decisions_payload = _read_json(decisions_path)
    result = validate_decisions_overlay(
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        source_prd=args.source_prd,
    )
    assert_review_artifact_is_sanitized(result)
    _write_json(output_json, result)
    _write_markdown(output_md, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.validate_only:
        return 0 if bool(result.get("valid")) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

