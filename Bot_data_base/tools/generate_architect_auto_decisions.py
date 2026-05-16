from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.architect_auto_decision_policy import generate_auto_decisions
from review.architect_review_pass import (
    build_architect_decisions_template,
    build_no_mutation_proof,
    queue_alignment_summary,
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


def _render_auto_decisions_markdown(*, source_prd: str, policy_report: dict[str, Any], validation: dict[str, Any]) -> str:
    lines = [
        f"# {source_prd} AUTO DECISIONS REPORT",
        "",
        "## Summary",
        f"- policy_version: {policy_report.get('policy_version')}",
        f"- items_total: {policy_report.get('items_total')}",
        f"- approved_count: {policy_report.get('approved_count')}",
        f"- needs_edit_count: {policy_report.get('needs_edit_count')}",
        f"- rejected_count: {policy_report.get('rejected_count')}",
        f"- defer_count: {policy_report.get('defer_count')}",
        f"- practice_items_count: {policy_report.get('practice_items_count')}",
        f"- quote_items_count: {policy_report.get('quote_items_count')}",
        f"- sensitive_items_count: {policy_report.get('sensitive_items_count')}",
        f"- official_overlay_updated: {policy_report.get('official_overlay_updated')}",
        f"- validation_valid: {validation.get('valid')}",
        f"- apply_ready: {validation.get('apply_ready')}",
        "",
        "## By Chunk Type",
    ]

    by_chunk = policy_report.get("by_chunk_type") if isinstance(policy_report.get("by_chunk_type"), dict) else {}
    if by_chunk:
        for key, value in by_chunk.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## By Review Priority"])
    by_priority = policy_report.get("by_review_priority") if isinstance(policy_report.get("by_review_priority"), dict) else {}
    if by_priority:
        for key, value in by_priority.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## By Reason Code"])
    by_reason = policy_report.get("by_reason_code") if isinstance(policy_report.get("by_reason_code"), dict) else {}
    if by_reason:
        for key, value in by_reason.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## Decision Samples"])
    samples = policy_report.get("samples") if isinstance(policy_report.get("samples"), dict) else {}
    for decision_kind in ("approved", "needs_edit", "rejected", "defer"):
        lines.append("")
        lines.append(f"### {decision_kind}")
        rows = samples.get(decision_kind) if isinstance(samples.get(decision_kind), list) else []
        if not rows:
            lines.append("- none")
            continue
        for row in rows:
            lines.append(
                f"- {row.get('review_item_id')} / {row.get('block_id')}: reason={row.get('reason')} edited_fields={row.get('edited_fields_keys')}"
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate conservative architect auto-decisions overlay for review queue.")
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument(
        "--batches-index",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_review_batches_index.json",
    )
    parser.add_argument(
        "--base-overlay",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_decisions_overlay.json",
    )
    parser.add_argument("--source-prd", default="PRD-046.0.9.3")
    parser.add_argument("--expected-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--expected-queue-count", type=int, default=87)
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.9.3")
    parser.add_argument(
        "--official-overlay",
        default="TO_DO_LIST/logs/PRD-046.0.9.2/architect_decisions_overlay.json",
    )
    parser.add_argument("--skip-official-overlay-update", action="store_true")
    parser.add_argument(
        "--out-md-auto",
        default="TO_DO_LIST/reports/PRD-046.0.9.3_AUTO_DECISIONS_REPORT.md",
    )
    parser.add_argument(
        "--out-md-validation",
        default="TO_DO_LIST/reports/PRD-046.0.9.3_DECISIONS_VALIDATION_REPORT.md",
    )
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    args = parser.parse_args()

    queue_path = find_fresh_review_queue(Path(args.review_queue))
    blocks_path = Path(args.blocks)
    batches_index_path = Path(args.batches_index)
    base_overlay_path = Path(args.base_overlay)
    official_overlay_path = Path(args.official_overlay)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md_auto = Path(args.out_md_auto)
    out_md_validation = Path(args.out_md_validation)
    registry_path = Path(args.registry)
    chroma_snapshot_path = Path(args.chroma_snapshot)

    if not queue_path.exists() or not blocks_path.exists() or not batches_index_path.exists() or not base_overlay_path.exists():
        raise FileNotFoundError("required_input_artifact_missing")

    queue_payload = read_json(queue_path)
    blocks_payload = read_json(blocks_path)
    batches_index = read_json(batches_index_path)

    if not isinstance(queue_payload, dict):
        raise RuntimeError("review_queue_must_be_object")
    if not isinstance(batches_index, dict):
        raise RuntimeError("batches_index_must_be_object")

    queue_source_prd = str(queue_payload.get("source_prd") or "")
    expected_source_prd = str(args.expected_source_prd)
    expected_queue_count = int(args.expected_queue_count)

    alignment = queue_alignment_summary(queue_payload, blocks_payload)
    queue_count = int(alignment.get("queue_items_count") or 0)
    queue_missing = int(alignment.get("queue_block_ids_missing") or 0)
    batches_queue_count = int(batches_index.get("queue_items_count") or 0)

    if queue_source_prd != expected_source_prd:
        raise RuntimeError("source_prd_mismatch")
    if expected_queue_count >= 0 and queue_count != expected_queue_count:
        raise RuntimeError("queue_items_count_mismatch")
    if expected_queue_count >= 0 and batches_queue_count != expected_queue_count:
        raise RuntimeError("batches_index_queue_count_mismatch")
    if queue_missing > 0:
        raise RuntimeError("queue_block_alignment_missing")

    decisions, policy_stats = generate_auto_decisions(
        queue_payload=queue_payload,
        blocks_payload=blocks_payload,
        source_prd=str(args.source_prd),
    )

    overlay_payload = build_architect_decisions_template(
        source_prd=str(args.source_prd),
        queue_source_prd=queue_source_prd,
        review_queue_hash=sha256_file(queue_path),
        blocks_hash_before=sha256_file(blocks_path),
    )
    overlay_payload["decision_owner"] = "architect_auto_policy"
    overlay_payload["ready_for_architect_review"] = False
    overlay_payload["apply_ready"] = False
    overlay_payload["decisions"] = decisions

    overlay_out = out_dir / "architect_auto_decisions_overlay.json"
    write_json(overlay_out, overlay_payload)

    validation = validate_architect_decisions_overlay(
        queue_payload=queue_payload,
        decisions_payload=overlay_payload,
        blocks_payload=blocks_payload,
        source_prd=str(args.source_prd),
    )

    coverage = validation.get("coverage") if isinstance(validation.get("coverage"), dict) else {}
    coverage_ok = (
        int(coverage.get("queue_items_count") or 0) == int(coverage.get("unique_review_item_ids_count") or 0)
        and int(coverage.get("remaining_items_count") or 0) == 0
    )
    safety_lists_empty = all(
        len(validation.get(key) or []) == 0
        for key in (
            "forbidden_key_hits",
            "secret_like_hits",
            "duplicate_review_item_ids",
            "unknown_review_item_ids",
            "block_id_mismatches",
            "authority_field_mutation_attempts",
            "invalid_decision_values",
        )
    )

    overlay_payload["apply_ready"] = bool(validation.get("valid")) and bool(validation.get("apply_ready"))
    overlay_payload["ready_for_architect_review"] = False
    write_json(overlay_out, overlay_payload)

    validation_out = out_dir / "architect_auto_decisions_validation.json"
    write_json(validation_out, validation)

    official_overlay_updated = False
    if (
        not bool(args.skip_official_overlay_update)
        and bool(validation.get("valid"))
        and bool(validation.get("apply_ready"))
        and coverage_ok
        and safety_lists_empty
        and queue_count == expected_queue_count
    ):
        write_json(official_overlay_path, overlay_payload)
        official_overlay_updated = True

    policy_stats["official_overlay_updated"] = official_overlay_updated
    policy_report_out = out_dir / "architect_auto_decisions_policy_report.json"
    write_json(policy_report_out, policy_stats)

    auto_report_text = _render_auto_decisions_markdown(
        source_prd=str(args.source_prd),
        policy_report=policy_stats,
        validation=validation,
    )
    write_text(out_md_auto, auto_report_text)

    validation_report_text = render_architect_validation_markdown(validation, source_prd=str(args.source_prd))
    write_text(out_md_validation, validation_report_text)

    chroma_count = read_optional_chroma_count(chroma_snapshot_path)
    no_mutation = build_no_mutation_proof(
        source_prd=str(args.source_prd),
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        decisions_overlay_path=overlay_out,
        blocks_hash_before=sha256_file(blocks_path),
        registry_hash_before=sha256_file(registry_path) if registry_path.exists() else "",
        chroma_count_before=chroma_count,
        chroma_count_after=chroma_count,
    )
    write_json(out_dir / "no_mutation_proof.json", no_mutation)

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"review_queue_path={queue_path.as_posix()}",
            f"queue_items_count={queue_count}",
            f"batches_index_queue_items_count={batches_queue_count}",
            f"decisions_count={len(decisions)}",
            f"validation_valid={validation.get('valid')}",
            f"coverage_percent={(coverage.get('coverage_percent'))}",
            f"remaining_items_count={coverage.get('remaining_items_count')}",
            f"apply_ready={validation.get('apply_ready')}",
            f"official_overlay_updated={official_overlay_updated}",
            f"approved_count={policy_stats.get('approved_count')}",
            f"needs_edit_count={policy_stats.get('needs_edit_count')}",
            f"rejected_count={policy_stats.get('rejected_count')}",
            f"defer_count={policy_stats.get('defer_count')}",
            f"production_apply_performed={no_mutation.get('production_apply_performed')}",
            f"chroma_reindex_performed={no_mutation.get('chroma_reindex_performed')}",
        ]
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    status = {
        "ok": bool(validation.get("valid")) and bool(validation.get("apply_ready")) and coverage_ok and safety_lists_empty,
        "source_prd": args.source_prd,
        "queue_items_count": queue_count,
        "decisions_count": len(decisions),
        "coverage_percent": coverage.get("coverage_percent"),
        "remaining_items_count": coverage.get("remaining_items_count"),
        "apply_ready": validation.get("apply_ready"),
        "official_overlay_updated": official_overlay_updated,
        "out_dir": out_dir.as_posix(),
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if bool(status["ok"]) else 3


if __name__ == "__main__":
    raise SystemExit(main())
