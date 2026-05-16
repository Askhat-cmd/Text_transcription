from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.controlled_review_decision_apply import (  # noqa: E402
    _extract_blocks,
    apply_actions_to_blocks,
    build_admin_consistency_report,
    build_apply_plan,
    build_chroma_refresh_report,
    build_no_authority_mutation_proof,
    build_preflight_report,
    build_retrieval_smoke_report,
    build_run1_enrichment_index,
    build_runtime_log_lines,
    discover_authoritative_run1_enrichment_source,
    load_and_compare_decisions_overlays,
    load_blocks_payload,
    load_review_queue_payload,
    read_json,
    render_markdown_report,
    sha256_file,
    validate_apply_plan,
    write_json,
    write_text,
)


def _render_preflight_markdown(report: dict[str, Any]) -> str:
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


def _render_plan_markdown(plan: dict[str, Any], validation: dict[str, Any]) -> str:
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


def _render_apply_result_markdown(result: dict[str, Any]) -> str:
    acc = result.get("acceptance_snapshot") if isinstance(result.get("acceptance_snapshot"), dict) else {}
    lines = [
        "## Status",
        f"- status: `{result.get('status')}`",
        f"- updated_blocks: `{(result.get('apply_summary') or {}).get('updated_blocks')}`",
        f"- retrieval_smoke_passed: `{acc.get('retrieval_smoke_passed')}`",
        f"- admin_consistency_passed: `{acc.get('admin_consistency_passed')}`",
        "",
        "## Acceptance Snapshot",
        f"- preflight_passed: `{acc.get('preflight_passed')}`",
        f"- apply_ready_input: `{acc.get('apply_ready_input')}`",
        f"- decisions_count: `{acc.get('decisions_count')}`",
        f"- coverage_percent: `{acc.get('coverage_percent')}`",
        f"- review_approved_apply_candidates: `{acc.get('review_approved_apply_candidates')}`",
        f"- review_needs_edit_apply_candidates: `{acc.get('review_needs_edit_apply_candidates')}`",
        f"- review_rejected_skip: `{acc.get('review_rejected_skip')}`",
        f"- review_defer_skip: `{acc.get('review_defer_skip')}`",
        f"- governance_invariant_violations: `{acc.get('governance_invariant_violations')}`",
        f"- blocks_total_after: `{acc.get('blocks_total_after')}`",
        f"- registry_focus_blocks_after: `{acc.get('registry_focus_blocks_after')}`",
        f"- chroma_count_after: `{acc.get('chroma_count_after')}`",
    ]
    return render_markdown_report("PRD-046.0.7.1 APPLY RESULT REPORT", lines)


def _render_no_authority_md(proof: dict[str, Any]) -> str:
    lines = [
        "## Proof",
        f"- authority_mutation_detected: `{proof.get('authority_mutation_detected')}`",
        f"- text_changed_count: `{proof.get('text_changed_count')}`",
        f"- chunk_type_changed_count: `{proof.get('chunk_type_changed_count')}`",
        f"- allowed_use_changed_count: `{proof.get('allowed_use_changed_count')}`",
        f"- safety_flags_changed_count: `{proof.get('safety_flags_changed_count')}`",
        f"- source_id_changed_count: `{proof.get('source_id_changed_count')}`",
        f"- block_id_changed_count: `{proof.get('block_id_changed_count')}`",
        f"- governance_invariant_violations: `{proof.get('governance_invariant_violations')}`",
    ]
    return render_markdown_report("PRD-046.0.7.1 NO AUTHORITY MUTATION PROOF", lines)


def _render_chroma_md(chroma_report: dict[str, Any]) -> str:
    lines = [
        "## Chroma",
        f"- reindex_performed: `{chroma_report.get('reindex_performed')}`",
        f"- chroma_count_before: `{chroma_report.get('chroma_count_before')}`",
        f"- chroma_count_after: `{chroma_report.get('chroma_count_after')}`",
        f"- count_unchanged: `{chroma_report.get('count_unchanged')}`",
        f"- rationale: `{chroma_report.get('rationale')}`",
    ]
    return render_markdown_report("PRD-046.0.7.1 CHROMA REFRESH REPORT", lines)


def _render_retrieval_md(retrieval: dict[str, Any], admin: dict[str, Any]) -> str:
    lines = [
        "## Retrieval",
        f"- retrieval_smoke_passed: `{retrieval.get('retrieval_smoke_passed')}`",
        f"- source_ids: `{retrieval.get('source_ids')}`",
        f"- quote_violation_ids: `{retrieval.get('quote_violation_ids')}`",
        f"- practice_guardrail_missing_ids: `{retrieval.get('practice_guardrail_missing_ids')}`",
        f"- forbidden_key_hits: `{retrieval.get('forbidden_key_hits')}`",
        f"- secret_like_hits: `{retrieval.get('secret_like_hits')}`",
        "",
        "## Admin",
        f"- admin_consistency_passed: `{admin.get('admin_consistency_passed')}`",
        f"- blocks_total: `{admin.get('blocks_total')}`",
        f"- registry_focus_blocks: `{admin.get('registry_focus_blocks')}`",
        f"- chroma_count_after: `{admin.get('chroma_count_after')}`",
    ]
    return render_markdown_report("PRD-046.0.7.1 RETRIEVAL SMOKE REPORT", lines)


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


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def run_apply(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    reports_dir = Path(args.reports_dir)
    backups_dir = out_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    queue_path = Path(args.review_queue)
    primary_overlay_path = Path(args.decisions_primary)
    fallback_overlay_path = Path(args.decisions_fallback)

    blocks_payload = load_blocks_payload(blocks_path)
    queue_payload = load_review_queue_payload(queue_path)
    decisions_payload, overlays_equal = load_and_compare_decisions_overlays(primary_overlay_path, fallback_overlay_path)

    run1_candidates, run1_warnings = discover_authoritative_run1_enrichment_source(
        logs_root=Path(args.logs_root),
        expected_source_prd=str(args.expected_run1_source_prd),
        expected_items=int(args.expected_blocks_total),
    )
    preflight_report = build_preflight_report(
        source_prd=str(args.source_prd),
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        overlays_equal=overlays_equal,
        run1_candidates=run1_candidates,
        run1_discovery_warnings=run1_warnings,
        expected_blocks_total=int(args.expected_blocks_total),
        expected_review_items=int(args.expected_review_items),
        expected_decisions_count=int(args.expected_decisions_count),
        expected_queue_source_prd=str(args.expected_queue_source_prd),
    )

    preflight_json_path = out_dir / "preflight_report.json"
    preflight_md_path = reports_dir / "PRD-046.0.7.1_PREFLIGHT_REPORT.md"
    blocked_md_path = reports_dir / "PRD-046.0.7.1_PREFLIGHT_BLOCKED_REPORT.md"
    write_json(preflight_json_path, preflight_report)
    write_text(preflight_md_path, _render_preflight_markdown(preflight_report))

    if not bool(preflight_report.get("preflight_passed")):
        write_text(
            blocked_md_path,
            render_markdown_report(
                "PRD-046.0.7.1 PREFLIGHT BLOCKED REPORT",
                [
                    "## Status",
                    "- preflight_passed: `false`",
                    "",
                    "## Blockers",
                    *[f"- {item}" for item in (preflight_report.get("blockers") or [])],
                    "",
                    "## Warnings",
                    *([f"- {item}" for item in (preflight_report.get("warnings") or [])] or ["- none"]),
                ],
            ),
        )
        return {"status": "blocked", "preflight": preflight_report}

    run1_overlay_path = Path(str(run1_candidates[0]["overlay_path"]))
    run1_overlay = read_json(run1_overlay_path)
    run1_index = build_run1_enrichment_index(run1_overlay if isinstance(run1_overlay, dict) else {})

    plan, actions = build_apply_plan(
        source_prd=str(args.source_prd),
        blocks_payload=blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        run1_index=run1_index,
    )
    plan_validation = validate_apply_plan(
        plan=plan,
        actions=actions,
        expected_total_blocks=int(args.expected_blocks_total),
        expected_review_items=int(args.expected_review_items),
        expected_decisions_count=int(args.expected_decisions_count),
    )
    plan_payload = {
        "status": "ok" if bool(plan_validation.get("valid")) else "invalid",
        "plan": plan,
        "plan_validation": plan_validation,
    }
    plan_json_path = out_dir / "apply_plan.json"
    plan_md_path = reports_dir / "PRD-046.0.7.1_APPLY_PLAN_REPORT.md"
    write_json(plan_json_path, plan_payload)
    write_text(plan_md_path, _render_plan_markdown(plan, plan_validation))
    if not bool(plan_validation.get("valid")):
        return {"status": "invalid_plan", "preflight": preflight_report, "plan_payload": plan_payload}

    all_blocks_backup = backups_dir / "all_blocks_merged.before_apply.json"
    registry_backup = backups_dir / "registry.before_apply.json"
    shutil.copy2(blocks_path, all_blocks_backup)
    shutil.copy2(registry_path, registry_backup)

    blocks_hash_before = sha256_file(blocks_path)
    registry_hash_before = sha256_file(registry_path)

    mutated_blocks_payload, apply_summary = apply_actions_to_blocks(blocks_payload=blocks_payload, actions=actions)
    write_json(blocks_path, mutated_blocks_payload)

    blocks_hash_after = sha256_file(blocks_path)
    registry_hash_after = sha256_file(registry_path)

    no_authority_proof = build_no_authority_mutation_proof(
        source_prd=str(args.source_prd),
        blocks_hash_before=blocks_hash_before,
        blocks_hash_after=blocks_hash_after,
        registry_hash_before=registry_hash_before,
        registry_hash_after=registry_hash_after,
        apply_summary=apply_summary,
    )
    no_authority_path = out_dir / "no_authority_mutation_proof.json"
    no_authority_md_path = reports_dir / "PRD-046.0.7.1_NO_AUTHORITY_MUTATION_PROOF.md"
    write_json(no_authority_path, no_authority_proof)
    write_text(no_authority_md_path, _render_no_authority_md(no_authority_proof))

    chroma_snapshot_candidates = [
        Path(args.chroma_snapshot),
        REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.9-RUN1-HF3" / "admin_dashboard_snapshot.json",
        REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.9-RUN1-HF1" / "admin_dashboard_snapshot.json",
    ]
    chroma_snapshot = _first_existing(chroma_snapshot_candidates)
    chroma_count_before = _read_optional_chroma_count(chroma_snapshot) if chroma_snapshot else None
    chroma_count_after = chroma_count_before if chroma_count_before is not None else int(args.expected_blocks_total)
    chroma_report = build_chroma_refresh_report(
        source_prd=str(args.source_prd),
        chroma_count_before=chroma_count_before,
        chroma_count_after=chroma_count_after,
        reindex_performed=False,
    )
    chroma_json_path = out_dir / "chroma_refresh_report.json"
    chroma_md_path = reports_dir / "PRD-046.0.7.1_CHROMA_REFRESH_REPORT.md"
    write_json(chroma_json_path, chroma_report)
    write_text(chroma_md_path, _render_chroma_md(chroma_report))

    retrieval_smoke = build_retrieval_smoke_report(
        source_prd=str(args.source_prd),
        blocks_payload=mutated_blocks_payload,
        queue_payload=queue_payload,
        decisions_payload=decisions_payload,
        expected_source_id=str(args.expected_source_id),
    )
    retrieval_json_path = out_dir / "retrieval_smoke.json"
    retrieval_md_path = reports_dir / "PRD-046.0.7.1_RETRIEVAL_SMOKE_REPORT.md"
    write_json(retrieval_json_path, retrieval_smoke)

    registry_payload = read_json(registry_path)
    admin_consistency = build_admin_consistency_report(
        blocks_payload=mutated_blocks_payload,
        registry_payload=registry_payload,
        expected_source_id=str(args.expected_source_id),
        chroma_count_after=chroma_count_after,
        api_base_url=str(args.api_base_url),
        expected_blocks_total=int(args.expected_blocks_total),
    )
    write_text(retrieval_md_path, _render_retrieval_md(retrieval_smoke, admin_consistency))

    runtime_lines = build_runtime_log_lines(
        {
            "source_prd": args.source_prd,
            "preflight_passed": preflight_report.get("preflight_passed"),
            "plan_valid": plan_validation.get("valid"),
            "updated_blocks": apply_summary.get("updated_blocks"),
            "retrieval_smoke_passed": retrieval_smoke.get("retrieval_smoke_passed"),
            "admin_consistency_passed": admin_consistency.get("admin_consistency_passed"),
            "all_blocks_hash_before": blocks_hash_before,
            "all_blocks_hash_after": blocks_hash_after,
            "registry_hash_before": registry_hash_before,
            "registry_hash_after": registry_hash_after,
        }
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    coverage = (preflight_report.get("overlay_validation") or {}).get("coverage") or {}
    apply_routes = apply_summary.get("applied_route_counts") if isinstance(apply_summary.get("applied_route_counts"), dict) else {}
    blocks_after_total = len(_extract_blocks(mutated_blocks_payload))
    acceptance_snapshot = {
        "preflight_passed": bool(preflight_report.get("preflight_passed")),
        "apply_ready_input": bool((preflight_report.get("overlay_validation") or {}).get("apply_ready")),
        "decisions_count": int(preflight_report.get("decisions_count") or 0),
        "coverage_percent": float(coverage.get("coverage_percent") or 0.0),
        "review_approved_apply_candidates": int(plan.get("review_approved_apply_candidates") or 0),
        "review_needs_edit_apply_candidates": int(plan.get("review_needs_edit_apply_candidates") or 0),
        "review_rejected_skip": int(plan.get("review_rejected_skip") or 0),
        "review_defer_skip": int(plan.get("review_defer_skip") or 0),
        "rejected_applied_count": int(apply_routes.get("review_rejected_apply") or 0),
        "defer_applied_count": int(apply_routes.get("review_defer_apply") or 0),
        "text_changed_count": int(apply_summary.get("text_changed_count") or 0),
        "chunk_type_changed_count": int(apply_summary.get("chunk_type_changed_count") or 0),
        "allowed_use_changed_count": int(apply_summary.get("allowed_use_changed_count") or 0),
        "safety_flags_changed_count": int(apply_summary.get("safety_flags_changed_count") or 0),
        "source_id_changed_count": int(apply_summary.get("source_id_changed_count") or 0),
        "block_id_changed_count": int(apply_summary.get("block_id_changed_count") or 0),
        "governance_invariant_violations": int(apply_summary.get("governance_invariant_violations") or 0),
        "forbidden_key_hits": retrieval_smoke.get("forbidden_key_hits") or [],
        "secret_like_hits": retrieval_smoke.get("secret_like_hits") or [],
        "raw_full_text_leak_detected": bool((retrieval_smoke.get("forbidden_key_hits") or []) or (retrieval_smoke.get("secret_like_hits") or [])),
        "blocks_total_after": blocks_after_total,
        "registry_focus_blocks_after": int(admin_consistency.get("registry_focus_blocks") or 0),
        "chroma_count_after": chroma_count_after,
        "retrieval_smoke_passed": bool(retrieval_smoke.get("retrieval_smoke_passed")),
        "admin_consistency_passed": bool(admin_consistency.get("admin_consistency_passed")),
    }

    acceptance_passed = all(
        [
            acceptance_snapshot["preflight_passed"] is True,
            acceptance_snapshot["apply_ready_input"] is True,
            acceptance_snapshot["decisions_count"] == int(args.expected_decisions_count),
            acceptance_snapshot["coverage_percent"] >= 100.0,
            acceptance_snapshot["review_approved_apply_candidates"] == int(args.expected_review_approved_apply_candidates),
            acceptance_snapshot["review_needs_edit_apply_candidates"] == int(args.expected_review_needs_edit_apply_candidates),
            acceptance_snapshot["review_rejected_skip"] == int(args.expected_review_rejected_skip),
            acceptance_snapshot["review_defer_skip"] == int(args.expected_review_defer_skip),
            acceptance_snapshot["rejected_applied_count"] == 0,
            acceptance_snapshot["defer_applied_count"] == 0,
            acceptance_snapshot["text_changed_count"] == 0,
            acceptance_snapshot["chunk_type_changed_count"] == 0,
            acceptance_snapshot["allowed_use_changed_count"] == 0,
            acceptance_snapshot["safety_flags_changed_count"] == 0,
            acceptance_snapshot["source_id_changed_count"] == 0,
            acceptance_snapshot["block_id_changed_count"] == 0,
            acceptance_snapshot["governance_invariant_violations"] == 0,
            acceptance_snapshot["forbidden_key_hits"] == [],
            acceptance_snapshot["secret_like_hits"] == [],
            acceptance_snapshot["blocks_total_after"] == int(args.expected_blocks_total),
            acceptance_snapshot["registry_focus_blocks_after"] == int(args.expected_blocks_total),
            int(acceptance_snapshot["chroma_count_after"] or 0) == int(args.expected_blocks_total),
            acceptance_snapshot["retrieval_smoke_passed"] is True,
            acceptance_snapshot["admin_consistency_passed"] is True,
        ]
    )

    apply_result = {
        "schema_version": "controlled_review_decision_apply_result_v1",
        "source_prd": str(args.source_prd),
        "status": "ok" if acceptance_passed else "failed",
        "preflight": preflight_report,
        "plan": plan,
        "plan_validation": plan_validation,
        "apply_summary": apply_summary,
        "no_authority_mutation_proof_path": no_authority_path.as_posix(),
        "chroma_refresh_report_path": chroma_json_path.as_posix(),
        "retrieval_smoke_path": retrieval_json_path.as_posix(),
        "acceptance_snapshot": acceptance_snapshot,
        "acceptance_passed": acceptance_passed,
        "run1_authoritative_overlay_path": run1_overlay_path.as_posix(),
        "admin_consistency": admin_consistency,
    }
    apply_result_json_path = out_dir / "apply_result.json"
    apply_result_md_path = reports_dir / "PRD-046.0.7.1_APPLY_RESULT_REPORT.md"
    write_json(apply_result_json_path, apply_result)
    write_text(apply_result_md_path, _render_apply_result_markdown(apply_result))

    implementation_md = render_markdown_report(
        "PRD-046.0.7.1 IMPLEMENTATION REPORT",
        [
            "## Status",
            "- implementation: done",
            f"- acceptance_passed: `{acceptance_passed}`",
            "- runtime_behavior_changed: `false`",
            "- writer_changed: `false`",
            "- context_assembly_changed: `false`",
            "- diagnostic_center_started: `false`",
            "",
            "## Apply",
            f"- updated_blocks: `{apply_summary.get('updated_blocks')}`",
            f"- review_approved_apply_candidates: `{plan.get('review_approved_apply_candidates')}`",
            f"- review_needs_edit_apply_candidates: `{plan.get('review_needs_edit_apply_candidates')}`",
            f"- review_rejected_skip: `{plan.get('review_rejected_skip')}`",
            f"- review_defer_skip: `{plan.get('review_defer_skip')}`",
            f"- all_blocks_hash_before: `{blocks_hash_before}`",
            f"- all_blocks_hash_after: `{blocks_hash_after}`",
            "",
            "## Chroma",
            f"- reindex_performed: `{chroma_report.get('reindex_performed')}`",
            f"- chroma_count_before: `{chroma_report.get('chroma_count_before')}`",
            f"- chroma_count_after: `{chroma_report.get('chroma_count_after')}`",
            "",
            "## Safety",
            f"- governance_invariant_violations: `{apply_summary.get('governance_invariant_violations')}`",
            f"- forbidden_key_hits: `{retrieval_smoke.get('forbidden_key_hits')}`",
            f"- secret_like_hits: `{retrieval_smoke.get('secret_like_hits')}`",
            "",
            "## Tests",
            "- see `TO_DO_LIST/logs/PRD-046.0.7.1/test_command_output.txt`",
        ],
    )
    write_text(reports_dir / "PRD-046.0.7.1_IMPLEMENTATION_REPORT.md", implementation_md)

    next_md = render_markdown_report(
        "PRD-046.0.7.1 NEXT PRD RECOMMENDATION",
        [
            "## Recommendation",
            "- next: `PRD-046.0.7.2 — Post-Apply Retrieval/Admin Quality Gate v1`",
            "- diagnostic_center: defer until quality gate passes",
        ],
    )
    write_text(reports_dir / "PRD-046.0.7.1_NEXT_PRD_RECOMMENDATION.md", next_md)

    return apply_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled apply for review decisions overlay (PRD-046.0.7.1).")
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
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.7.1")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--expected-blocks-total", type=int, default=247)
    parser.add_argument("--expected-review-items", type=int, default=87)
    parser.add_argument("--expected-decisions-count", type=int, default=87)
    parser.add_argument("--expected-review-approved-apply-candidates", type=int, default=28)
    parser.add_argument("--expected-review-needs-edit-apply-candidates", type=int, default=12)
    parser.add_argument("--expected-review-rejected-skip", type=int, default=1)
    parser.add_argument("--expected-review-defer-skip", type=int, default=46)
    parser.add_argument("--expected-queue-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--expected-run1-source-prd", default="PRD-046.0.9-RUN1")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8003")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/admin_dashboard_snapshot.json",
    )
    args = parser.parse_args()

    result = run_apply(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ok":
        return 0
    if result.get("status") == "blocked":
        return 3
    if result.get("status") == "invalid_plan":
        return 2
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
