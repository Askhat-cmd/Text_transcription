from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.controlled_review_decision_apply import (  # noqa: E402
    build_preflight_report,
    discover_authoritative_run1_enrichment_source,
    load_and_compare_decisions_overlays,
    load_blocks_payload,
    load_review_queue_payload,
    read_json,
    render_markdown_report,
    validate_architect_decisions_overlay,
    write_json,
    write_text,
)


def _render_preflight_markdown(report: dict) -> str:
    lines = [
        "## Status",
        f"- preflight_passed: `{report.get('preflight_passed')}`",
        f"- blocks_total: `{report.get('blocks_total')}`",
        f"- queue_items_count: `{report.get('queue_items_count')}`",
        f"- decisions_count: `{report.get('decisions_count')}`",
        f"- overlay_primary_fallback_equal: `{report.get('overlay_primary_fallback_equal')}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    if blockers:
        lines.extend([f"- {item}" for item in blockers])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")
    return render_markdown_report("PRD-046.0.7.1 PREFLIGHT REPORT", lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks for controlled review decision apply.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.1")
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument(
        "--decisions-primary",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_decisions_overlay.json",
    )
    parser.add_argument(
        "--decisions-fallback",
        default="TO_DO_LIST/logs/PRD-046.0.9.3/architect_auto_decisions_overlay.json",
    )
    parser.add_argument("--logs-root", default="TO_DO_LIST/logs")
    parser.add_argument("--expected-blocks-total", type=int, default=247)
    parser.add_argument("--expected-review-items", type=int, default=87)
    parser.add_argument("--expected-decisions-count", type=int, default=87)
    parser.add_argument("--expected-queue-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--expected-run1-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--out", default="TO_DO_LIST/logs/PRD-046.0.7.1/preflight_report.json")
    parser.add_argument("--out-md", default="TO_DO_LIST/reports/PRD-046.0.7.1_PREFLIGHT_REPORT.md")
    parser.add_argument(
        "--blocked-md",
        default="TO_DO_LIST/reports/PRD-046.0.7.1_PREFLIGHT_BLOCKED_REPORT.md",
    )
    args = parser.parse_args()

    blocks_payload = load_blocks_payload(Path(args.blocks))
    queue_payload = load_review_queue_payload(Path(args.review_queue))
    decisions_payload, overlays_equal = load_and_compare_decisions_overlays(
        Path(args.decisions_primary),
        Path(args.decisions_fallback),
    )

    run1_candidates, discovery_warnings = discover_authoritative_run1_enrichment_source(
        logs_root=Path(args.logs_root),
        expected_source_prd=str(args.expected_run1_source_prd),
        expected_items=int(args.expected_blocks_total),
    )

    report = build_preflight_report(
        source_prd=str(args.source_prd),
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        overlays_equal=overlays_equal,
        run1_candidates=run1_candidates,
        run1_discovery_warnings=discovery_warnings,
        expected_blocks_total=int(args.expected_blocks_total),
        expected_review_items=int(args.expected_review_items),
        expected_decisions_count=int(args.expected_decisions_count),
        expected_queue_source_prd=str(args.expected_queue_source_prd),
    )
    write_json(Path(args.out), report)
    write_text(Path(args.out_md), _render_preflight_markdown(report))

    if not bool(report.get("preflight_passed")):
        blocked_text = render_markdown_report(
            "PRD-046.0.7.1 PREFLIGHT BLOCKED REPORT",
            [
                "## Status",
                "- preflight_passed: `false`",
                "",
                "## Blockers",
                *[f"- {item}" for item in (report.get("blockers") or [])],
                "",
                "## Warnings",
                *([f"- {item}" for item in (report.get("warnings") or [])] or ["- none"]),
            ],
        )
        write_text(Path(args.blocked_md), blocked_text)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if bool(report.get("preflight_passed")) else 3


if __name__ == "__main__":
    raise SystemExit(main())

