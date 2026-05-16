from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.controlled_review_decision_apply import (  # noqa: E402
    build_apply_plan,
    build_preflight_report,
    build_run1_enrichment_index,
    discover_authoritative_run1_enrichment_source,
    load_and_compare_decisions_overlays,
    load_blocks_payload,
    load_review_queue_payload,
    read_json,
    render_markdown_report,
    validate_apply_plan,
    write_json,
    write_text,
)


def _render_plan_markdown(plan: dict, validation: dict) -> str:
    lines = [
        "## Summary",
        f"- total_blocks: `{plan.get('total_blocks')}`",
        f"- review_items_count: `{plan.get('review_items_count')}`",
        f"- safe_non_review_apply_candidates: `{plan.get('safe_non_review_apply_candidates')}`",
        f"- review_approved_apply_candidates: `{plan.get('review_approved_apply_candidates')}`",
        f"- review_needs_edit_apply_candidates: `{plan.get('review_needs_edit_apply_candidates')}`",
        f"- review_rejected_skip: `{plan.get('review_rejected_skip')}`",
        f"- review_defer_skip: `{plan.get('review_defer_skip')}`",
        f"- max_expected_apply_candidates: `{plan.get('max_expected_apply_candidates')}`",
        f"- actual_apply_candidates: `{plan.get('actual_apply_candidates')}`",
        "",
        "## Validation",
        f"- valid: `{validation.get('valid')}`",
        "",
        "## Errors",
    ]
    errors = validation.get("errors") if isinstance(validation.get("errors"), list) else []
    if errors:
        lines.extend([f"- {item}" for item in errors])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = validation.get("warnings") if isinstance(validation.get("warnings"), list) else []
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")
    return render_markdown_report("PRD-046.0.7.1 APPLY PLAN REPORT", lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dry-run plan for controlled review decision apply.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.1")
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
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
    parser.add_argument("--out", default="TO_DO_LIST/logs/PRD-046.0.7.1/apply_plan.json")
    parser.add_argument("--out-md", default="TO_DO_LIST/reports/PRD-046.0.7.1_APPLY_PLAN_REPORT.md")
    args = parser.parse_args()

    blocks_payload = load_blocks_payload(Path(args.blocks))
    queue_payload = load_review_queue_payload(Path(args.review_queue))
    decisions_payload, overlays_equal = load_and_compare_decisions_overlays(
        Path(args.decisions_primary),
        Path(args.decisions_fallback),
    )

    candidates, warnings = discover_authoritative_run1_enrichment_source(
        logs_root=Path(args.logs_root),
        expected_source_prd=str(args.expected_run1_source_prd),
        expected_items=int(args.expected_blocks_total),
    )
    preflight = build_preflight_report(
        source_prd=str(args.source_prd),
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        overlays_equal=overlays_equal,
        run1_candidates=candidates,
        run1_discovery_warnings=warnings,
        expected_blocks_total=int(args.expected_blocks_total),
        expected_review_items=int(args.expected_review_items),
        expected_decisions_count=int(args.expected_decisions_count),
        expected_queue_source_prd=str(args.expected_queue_source_prd),
    )
    if not bool(preflight.get("preflight_passed")):
        write_json(Path(args.out), {"status": "blocked", "preflight": preflight})
        write_text(
            Path(args.out_md),
            render_markdown_report(
                "PRD-046.0.7.1 APPLY PLAN REPORT",
                ["## Status", "- blocked: `true`", "", "## Blockers", *[f"- {x}" for x in (preflight.get("blockers") or [])]],
            ),
        )
        print(json.dumps({"status": "blocked", "preflight": preflight}, ensure_ascii=False, indent=2))
        return 3

    run1_overlay = read_json(Path(candidates[0]["overlay_path"]))
    run1_index = build_run1_enrichment_index(run1_overlay if isinstance(run1_overlay, dict) else {})

    plan, actions = build_apply_plan(
        source_prd=str(args.source_prd),
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        run1_index=run1_index,
    )
    validation = validate_apply_plan(
        plan=plan,
        actions=actions,
        expected_total_blocks=int(args.expected_blocks_total),
        expected_review_items=int(args.expected_review_items),
        expected_decisions_count=int(args.expected_decisions_count),
    )
    payload = {"status": "ok" if bool(validation.get("valid")) else "invalid", "plan": plan, "plan_validation": validation}
    write_json(Path(args.out), payload)
    write_text(Path(args.out_md), _render_plan_markdown(plan, validation))

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if bool(validation.get("valid")) else 2


if __name__ == "__main__":
    raise SystemExit(main())

