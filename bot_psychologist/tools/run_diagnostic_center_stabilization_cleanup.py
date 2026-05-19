from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = cleanup.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def _render_stabilization_cleanup_report(*, source_gate: dict[str, Any], scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {PRD} Stabilization Cleanup Report",
            "",
            f"- PRD: `{PRD}`",
            f"- Final status: `{scorecard.get('final_status', 'blocked')}`",
            f"- Decision: `{scorecard.get('decision', 'blocked')}`",
            "",
            "## Source Gate",
            f"- `source_gate_passed={str(source_gate.get('source_gate_passed', False)).lower()}`",
            f"- `source_final_status={source_gate.get('final_status', 'blocked')}`",
            f"- `source_decision={source_gate.get('decision', 'blocked')}`",
            f"- `provider_scenarios_total={source_gate.get('provider_scenarios_total', 0)}`",
            f"- `normal_user_apply_count_total={source_gate.get('normal_user_apply_count_total', 0)}`",
            f"- `normal_user_provider_calls_total={source_gate.get('normal_user_provider_calls_total', 0)}`",
            f"- `rollback_failure_count_total={source_gate.get('rollback_failure_count_total', 0)}`",
            "",
            "## Cleanup Policy",
            "- Non-destructive manifest-first cleanup only.",
            "- Physical runtime/test/gate deletion is not performed in this PRD.",
            "",
            "## Decision",
            f"- `final_status={scorecard.get('final_status', 'blocked')}`",
            f"- `decision={scorecard.get('decision', 'blocked')}`",
            "",
        ]
    )


def _render_runtime_eval_harness_classification_report(
    *, classification: dict[str, Any], permanent_gate_revalidation: dict[str, Any]
) -> str:
    zone_counts = classification.get("zone_counts", {})
    lines = [
        f"# {PRD} Runtime/Eval Harness Classification Report",
        "",
        f"- PRD: `{PRD}`",
        "",
        "## Zone Counts",
    ]
    for zone, count in sorted(zone_counts.items()):
        lines.append(f"- `{zone}={count}`")
    lines.extend(
        [
            "",
            "## Required Zones",
            f"- `required_zones_present={str(classification.get('required_zones_present', False)).lower()}`",
            f"- `unknown_requires_review_count={classification.get('unknown_requires_review_count', 0)}`",
            "",
            "## Permanent Gate Revalidation",
            f"- `permanent_gate_revalidation_passed={str(permanent_gate_revalidation.get('permanent_gate_revalidation_passed', False)).lower()}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_docs_compaction_report(*, snapshot: dict[str, Any], compaction: dict[str, Any], docs_sync: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {PRD} Docs Compaction Report",
            "",
            f"- PRD: `{PRD}`",
            f"- `docs_snapshots_created={str(snapshot.get('created', False)).lower()}`",
            f"- `docs_compaction_passed={str(compaction.get('docs_compaction_passed', False)).lower()}`",
            f"- `runtime_map_created={str(compaction.get('runtime_map_created', False)).lower()}`",
            f"- `eval_harness_map_created={str(compaction.get('eval_harness_map_created', False)).lower()}`",
            "",
            "## Snapshot Directory",
            f"- `{snapshot.get('snapshot_dir', '')}`",
            "",
            "## Compacted Docs",
            *[f"- `{item}`" for item in compaction.get("compacted_docs", [])],
            "",
            "## Docs Sync",
            f"- `docs_synced={str(docs_sync.get('docs_synced', False)).lower()}`",
            f"- `adr_049_present={str(docs_sync.get('adr_049_present', False)).lower()}`",
            "",
        ]
    )


def _render_artifact_hygiene_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {PRD} Artifact Hygiene Normalization Report",
            "",
            f"- PRD: `{PRD}`",
            f"- `utf8_decode_error_count={payload.get('utf8_decode_error_count', 0)}`",
            f"- `nul_byte_file_count={payload.get('nul_byte_file_count', 0)}`",
            f"- `json_parse_error_count={payload.get('json_parse_error_count', 0)}`",
            f"- `current_generated_artifact_replacement_char_count={payload.get('current_generated_artifact_replacement_char_count', 0)}`",
            f"- `historical_warning_count={payload.get('historical_warning_count', 0)}`",
            f"- `historical_warning_documented={str(payload.get('historical_warning_documented', False)).lower()}`",
            f"- `artifact_hygiene_normalization_passed={str(payload.get('artifact_hygiene_normalization_passed', False)).lower()}`",
            "",
            f"- Historical warning source: {payload.get('historical_warning_source', 'none')}",
            "",
        ]
    )


def _render_permanent_gate_revalidation_report(payload: dict[str, Any]) -> str:
    lines = [
        f"# {PRD} Permanent Gate Revalidation Report",
        "",
        f"- PRD: `{PRD}`",
        f"- `permanent_gate_revalidation_passed={str(payload.get('permanent_gate_revalidation_passed', False)).lower()}`",
        "",
        "## Gate Checks",
    ]
    for key, value in sorted((payload.get("gate_checks") or {}).items()):
        lines.append(f"- `{key}={str(value).lower()}`")
    if payload.get("missing_gates"):
        lines.append("")
        lines.append("## Missing Gates")
        for item in payload.get("missing_gates", []):
            lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)


def _render_next_prd_recommendation(*, scorecard: dict[str, Any]) -> str:
    status = str(scorecard.get("final_status", "blocked"))
    if status == "passed":
        option = "A. ready_for_rollout_planning_prd"
        reason = "stabilization cleanup and permanent gate revalidation are passed; rollout planning can be prepared in separate PRD."
    else:
        option = "C. needs_cleanup_hotfix"
        reason = "stabilization cleanup gate has blockers and requires a targeted hotfix PRD before rollout planning."
    return "\n".join(
        [
            f"# {PRD} Next PRD Recommendation",
            "",
            f"- PRD: `{PRD}`",
            f"- Final status: `{status}`",
            f"- Decision option: `{option}`",
            f"- Recommended next PRD: `{cleanup.NEXT_PRD if status == 'passed' else 'PRD-046.1.29-HF1 - Cleanup / Docs / Eval Harness Hotfix'}`",
            "",
            f"Reason: {reason}",
            "",
        ]
    )


def _render_implementation_report(*, scorecard: dict[str, Any], commands: list[str]) -> str:
    blockers = scorecard.get("blockers", [])
    warnings = scorecard.get("warnings", [])
    return "\n".join(
        [
            f"# {PRD} Implementation Report",
            "",
            f"- PRD ID: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', 'blocked')}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.29_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_stabilization_cleanup_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_stabilization_cleanup.py",
            "- bot_psychologist/tools/run_diagnostic_center_stabilization_cleanup.py",
            "- bot_psychologist/tests/multiagent/test_stabilization_cleanup_*.py",
            "- docs/DIAGNOSTIC_CENTER_RUNTIME_MAP.md",
            "- docs/DIAGNOSTIC_CENTER_EVAL_HARNESS.md",
            "- TO_DO_LIST/reports/PRD-046.1.29_*.md",
            "",
            "## Commands Run",
            *[f"- `{cmd}`" for cmd in commands],
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            f"- warnings: `{', '.join(warnings) if warnings else 'none'}`",
            "",
            "## No-Mutation / Docs Sync",
            f"- `no_mutation_proof_passed={str(scorecard.get('no_mutation_proof_passed', False)).lower()}`",
            f"- `docs_compaction_passed={str(scorecard.get('docs_compaction_passed', False)).lower()}`",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(getattr(args, "repo_root", ".")).resolve()
    reports_dir = Path(getattr(args, "reports_dir", "TO_DO_LIST/reports")).resolve()
    logs_dir = Path(getattr(args, "logs_dir", "TO_DO_LIST/logs")).resolve()
    output_dir = Path(getattr(args, "output_dir", "TO_DO_LIST/logs/PRD-046.1.29")).resolve()
    strict = bool(getattr(args, "strict", False))
    write_doc_snapshots = bool(getattr(args, "write_doc_snapshots", False))
    compact_docs = bool(getattr(args, "compact_docs", False))

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text(f"{PRD} runner executed.\n", encoding="utf-8")

    tracked_paths, hash_before = cleanup.tracked_hashes(repo_root)

    preflight = cleanup.preflight_source_reports(reports_dir)
    source_gate = cleanup.build_source_gate(preflight)
    _write_json(output_dir / "source_gate.json", source_gate)

    inventory = cleanup.collect_artifact_inventory(repo_root)
    _write_json(output_dir / "artifact_inventory.json", inventory)

    classification, archive_manifest, cleanup_manifest = cleanup.classify_inventory(inventory)
    _write_json(output_dir / "artifact_classification.json", classification)
    _write_json(output_dir / "archive_manifest.json", archive_manifest)
    _write_json(output_dir / "cleanup_candidate_manifest.json", cleanup_manifest)

    snapshot_proof = cleanup.create_docs_snapshots(repo_root, write_snapshots=write_doc_snapshots)
    _write_json(output_dir / "docs_snapshot_proof.json", snapshot_proof)

    docs_compaction = cleanup.compact_docs(repo_root, compact=compact_docs, snapshot_proof=snapshot_proof)
    _write_json(output_dir / "docs_compaction_report.json", docs_compaction)

    permanent_gate_revalidation = cleanup.revalidate_permanent_gates(repo_root)
    _write_json(output_dir / "permanent_gate_revalidation.json", permanent_gate_revalidation)

    hash_after = {name: cleanup._sha256(path) if path.exists() else "missing" for name, path in tracked_paths.items()}
    no_mutation = cleanup.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation)

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(output_dir),
            reports_dir=str(reports_dir),
            out_dir=str(output_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    source_warning_text = str(preflight.get("texts", {}).get("implementation", ""))
    artifact_hygiene = cleanup.build_artifact_hygiene_normalization(
        encoding_report=encoding_report,
        source_warning_text=source_warning_text,
    )
    _write_json(output_dir / "artifact_hygiene_normalization.json", artifact_hygiene)

    decision_payload, scorecard = cleanup.build_decision(
        source_gate=source_gate,
        inventory=inventory,
        classification=classification,
        archive_manifest=archive_manifest,
        cleanup_manifest=cleanup_manifest,
        snapshot_proof=snapshot_proof,
        docs_compaction=docs_compaction,
        permanent_gates=permanent_gate_revalidation,
        artifact_hygiene=artifact_hygiene,
        no_mutation=no_mutation,
    )
    _write_json(output_dir / "stabilization_cleanup_decision.json", decision_payload)
    _write_json(output_dir / "stabilization_cleanup_scorecard.json", scorecard)

    # Compatibility outputs for older tests from PRD-046.1.15 lineage.
    _write_json(output_dir / "stabilization_source_gate.json", source_gate)
    _write_json(output_dir / "diagnostic_center_module_inventory.json", inventory)
    _write_json(output_dir / "diagnostic_center_module_classification.json", classification)
    _write_json(output_dir / "diagnostic_center_archive_manifest.json", archive_manifest)
    _write_json(output_dir / "diagnostic_center_cleanup_plan.json", cleanup_manifest)
    _write_json(output_dir / "diagnostic_center_regression_gate_catalog.json", permanent_gate_revalidation)
    _write_json(output_dir / "diagnostic_center_stabilization_scorecard.json", scorecard)

    docs_sync = cleanup.docs_sync_status(repo_root)

    stabilization_report = _render_stabilization_cleanup_report(source_gate=source_gate, scorecard=scorecard)
    classification_report = _render_runtime_eval_harness_classification_report(
        classification=classification,
        permanent_gate_revalidation=permanent_gate_revalidation,
    )
    docs_compaction_report = _render_docs_compaction_report(
        snapshot=snapshot_proof,
        compaction=docs_compaction,
        docs_sync=docs_sync,
    )
    artifact_hygiene_report = _render_artifact_hygiene_report(artifact_hygiene)
    permanent_report = _render_permanent_gate_revalidation_report(permanent_gate_revalidation)
    next_prd_report = _render_next_prd_recommendation(scorecard=scorecard)
    implementation_report = _render_implementation_report(
        scorecard=scorecard,
        commands=[
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_source_gate.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_inventory.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_classification.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_archive_manifest.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_docs_snapshot.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_docs_compaction.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_permanent_gates.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_artifact_hygiene.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_no_mutation.py",
            "python -m pytest bot_psychologist/tests/multiagent/test_stabilization_cleanup_decision_gate.py",
            "python -m bot_psychologist.tools.run_diagnostic_center_stabilization_cleanup --repo-root . --reports-dir TO_DO_LIST/reports --logs-dir TO_DO_LIST/logs --output-dir TO_DO_LIST/logs/PRD-046.1.29 --strict --write-doc-snapshots --compact-docs",
        ],
    )

    _write_text(reports_dir / "PRD-046.1.29_STABILIZATION_CLEANUP_REPORT.md", stabilization_report)
    _write_text(
        reports_dir / "PRD-046.1.29_RUNTIME_EVAL_HARNESS_CLASSIFICATION_REPORT.md",
        classification_report,
    )
    _write_text(reports_dir / "PRD-046.1.29_DOCS_COMPACTION_REPORT.md", docs_compaction_report)
    _write_text(
        reports_dir / "PRD-046.1.29_ARTIFACT_HYGIENE_NORMALIZATION_REPORT.md",
        artifact_hygiene_report,
    )
    _write_text(
        reports_dir / "PRD-046.1.29_PERMANENT_GATE_REVALIDATION_REPORT.md",
        permanent_report,
    )
    _write_text(reports_dir / "PRD-046.1.29_NEXT_PRD_RECOMMENDATION.md", next_prd_report)
    _write_text(reports_dir / "PRD-046.1.29_IMPLEMENTATION_REPORT.md", implementation_report)

    _append_text(
        test_log,
        "\n".join(
            [
                "",
                f"{PRD} runner summary:",
                json.dumps(
                    {
                        "status": scorecard.get("final_status", "blocked"),
                        "decision": scorecard.get("decision", "blocked"),
                    },
                    ensure_ascii=False,
                ),
                "",
            ]
        ),
    )

    if strict and scorecard.get("final_status") != "passed":
        return {
            "status": "blocked",
            "decision": scorecard.get("decision", "blocked"),
            "scorecard": scorecard,
            "preflight": preflight,
            "docs_sync": docs_sync,
        }

    return {
        "status": scorecard.get("final_status", "blocked"),
        "decision": scorecard.get("decision", "blocked"),
        "scorecard": scorecard,
        "preflight": preflight,
        "docs_sync": docs_sync,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.29 stabilization cleanup gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--logs-dir", default="TO_DO_LIST/logs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.29")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-doc-snapshots", action="store_true")
    parser.add_argument("--compact-docs", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
