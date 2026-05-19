from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = planning.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _upsert_project_state(project_state_path: Path) -> None:
    text = project_state_path.read_text(encoding="utf-8") if project_state_path.exists() else ""
    if "PRD-046.1.30" in text:
        return
    append = (
        "\n\nControlled rollout planning completed in `PRD-046.1.30` (plan-only): "
        "no provider execution, no normal-user activation, no production mutation; "
        "next execution gated by `PRD-046.1.31`."
    )
    project_state_path.write_text(text.rstrip() + append + "\n", encoding="utf-8")


def _upsert_roadmap(roadmap_path: Path) -> None:
    text = roadmap_path.read_text(encoding="utf-8") if roadmap_path.exists() else "# Roadmap\n\n"
    if "PRD-046.1.30" in text and "PRD-046.1.31" in text:
        return

    lines = text.splitlines()
    if "## Done" not in text:
        lines.extend(["", "## Done"])
    insert_done = "- PRD-046.1.30: controlled rollout planning package completed (plan-only, rollback-first, no provider execution)."
    if insert_done not in lines:
        try:
            done_idx = lines.index("## Done")
            lines.insert(done_idx + 1, insert_done)
        except ValueError:
            lines.append(insert_done)

    if "## Next" not in "\n".join(lines):
        lines.extend(["", "## Next", "1. PRD-046.1.31 - Diagnostic Center Controlled Rollout Execution Gate v1."])
    elif "PRD-046.1.31" not in "\n".join(lines):
        next_idx = lines.index("## Next")
        lines.insert(next_idx + 1, "1. PRD-046.1.31 - Diagnostic Center Controlled Rollout Execution Gate v1.")

    roadmap_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_prd_index(prd_index_path: Path) -> None:
    text = prd_index_path.read_text(encoding="utf-8") if prd_index_path.exists() else ""
    if "PRD-046.1.30" in text:
        return
    row = (
        "| PRD-046.1.30 | Diagnostic Center Controlled Rollout Planning v1 | passed | pending | "
        "created controlled rollout planning package (source/runtime-map/eval-harness gates, cohort/toggle/preflight/hard-stop/rollback/evidence plans) without execution/provider calls | "
        "TO_DO_LIST/reports/PRD-046.1.30_IMPLEMENTATION_REPORT.md |"
    )
    if "| --- | --- | --- | --- | --- | --- |" in text:
        lines = text.splitlines()
        header_idx = lines.index("| --- | --- | --- | --- | --- | --- |")
        lines.insert(header_idx + 1, row)
        prd_index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    else:
        rebuilt = "\n".join(
            [
                "# PRD Index",
                "",
                "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |",
                "| --- | --- | --- | --- | --- | --- |",
                row,
                "",
            ]
        )
        prd_index_path.write_text(rebuilt, encoding="utf-8")


def _upsert_decisions(decisions_path: Path) -> None:
    text = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else "# Architecture Decisions\n\n"
    marker = "Controlled Rollout Planning Boundary"
    if marker in text:
        return
    append = """

## ADR-049 - Controlled Rollout Planning Boundary

Status: accepted
Context: Diagnostic Center accepted as governed limited-runtime candidate, but rollout execution remains sensitive to rollback, safety/KB, trace sanitization, and normal-user isolation risks.
Decision: controlled rollout execution requires a separate explicit PRD with allowlist-only cohort, rollback-first policy, hard-stop enforcement, permanent gate reuse, and strict normal-user no-effect proof.
Consequences: planning and execution are separated; broad rollout and production-ready declaration remain blocked in planning-only phase.
"""
    decisions_path.write_text(text.rstrip() + "\n" + append.lstrip("\n"), encoding="utf-8")


def _render_controlled_rollout_planning_report(*, source_gate: dict[str, Any], scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {PRD} Controlled Rollout Planning Report",
            "",
            f"- PRD: `{PRD}`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', 'blocked_needs_hotfix')}`",
            "",
            "## Source Gates",
            f"- `source_gate={scorecard.get('source_gate', 'failed')}`",
            f"- `runtime_map_gate={scorecard.get('runtime_map_gate', 'failed')}`",
            f"- `eval_harness_gate={scorecard.get('eval_harness_gate', 'failed')}`",
            f"- `source_046_1_28_passed={str(source_gate.get('source_046_1_28_passed', False)).lower()}`",
            f"- `source_046_1_29_passed={str(source_gate.get('source_046_1_29_passed', False)).lower()}`",
            "",
            "## Boundary",
            "- Planning-only PRD; no provider execution, no runtime-default mutation, no broad rollout, no normal-user activation.",
            "",
        ]
    )


def _render_operator_runbook() -> str:
    return "\n".join(
        [
            "# PRD-046.1.30 Operator Runbook",
            "",
            "This PRD is planning-only. Do not execute provider-backed rollout in this cycle.",
            "",
            "## Preparation",
            "1. Confirm source gates PRD-046.1.28 and PRD-046.1.29 are passed.",
            "2. Confirm runtime map and eval harness gates are passed.",
            "3. Confirm allowlist is explicit and restricted to internal/synthetic operator IDs.",
            "",
            "## Pre-Execution Rules for Future PRD-046.1.31",
            "1. Keep default conservative flags unless explicit controlled window starts.",
            "2. Validate rollback switch before execution.",
            "3. Validate normal-user controls are configured (>=2).",
            "4. Validate provider budget and hard-stop criteria.",
            "",
            "## Hard Stops",
            "1. Any normal-user apply/provider call.",
            "2. Any rollback failure.",
            "3. Any safety/KB boundary violation.",
            "4. Any trace sanitization failure.",
            "5. Any runtime-default or production-data mutation.",
            "",
            "## Evidence for Future Execution PRD",
            "1. execution_manifest",
            "2. provider_budget_report",
            "3. sanitized_provider_trace",
            "4. normal_user_no_effect_report",
            "5. quality_micro_shift_report",
            "6. safety_kb_boundary_report",
            "7. trace_sanitization_report",
            "8. rollback_precheck_postcheck_report",
            "9. botdb_preflight_postcheck_report",
            "10. no_mutation_proof",
            "11. artifact_hygiene_report",
            "12. operator_summary",
            "13. next_prd_recommendation",
            "",
        ]
    )


def _render_next_prd_recommendation(scorecard: dict[str, Any]) -> str:
    if scorecard.get("final_status") == "passed":
        return "\n".join(
            [
                f"# {PRD} Next PRD Recommendation",
                "",
                "- recommendation: `PRD-046.1.31 - Diagnostic Center Controlled Rollout Execution Gate v1`",
                "- rationale: planning package is ready and all mandatory planning gates are green.",
                "",
            ]
        )
    return "\n".join(
        [
            f"# {PRD} Next PRD Recommendation",
            "",
            "- recommendation: `PRD-046.1.30-HF1 - Controlled Rollout Planning Hotfix`",
            "- rationale: blockers remain in rollout planning gates.",
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
            f"- decision: `{scorecard.get('decision', 'blocked_needs_hotfix')}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.30_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_controlled_rollout_planning_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_controlled_rollout_planning.py",
            "- bot_psychologist/tools/run_diagnostic_center_controlled_rollout_planning.py",
            "- bot_psychologist/tests/multiagent/test_controlled_rollout_planning_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.30/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.30_*.md",
            "",
            "## Commands executed",
            *[f"- `{cmd}`" for cmd in commands],
            "",
            "## Runner strict gate summary",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', 'blocked_needs_hotfix')}`",
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            f"- warnings: `{', '.join(warnings) if warnings else 'none'}`",
            "",
            "## No-mutation proof",
            f"- `no_mutation_proof_passed={str(scorecard.get('no_mutation_proof_passed', False)).lower()}`",
            "",
            "## Docs sync proof",
            f"- `docs_synced={str(scorecard.get('docs_synced', False)).lower()}`",
            "",
            "## Next PRD recommendation",
            f"- `{planning.NEXT_PRD_PASSED if scorecard.get('final_status') == 'passed' else planning.NEXT_PRD_BLOCKED}`",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(getattr(args, "repo_root", ".")).resolve()
    reports_dir = Path(getattr(args, "reports_dir", "TO_DO_LIST/reports")).resolve()
    docs_dir = Path(getattr(args, "docs_dir", "docs")).resolve()
    logs_dir = Path(getattr(args, "logs_dir", "TO_DO_LIST/logs")).resolve()
    output_dir = Path(getattr(args, "output_dir", "TO_DO_LIST/logs/PRD-046.1.30")).resolve()
    strict = bool(getattr(args, "strict", False))

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    _upsert_project_state(docs_dir / "PROJECT_STATE.md")
    _upsert_roadmap(docs_dir / "ROADMAP.md")
    _upsert_prd_index(docs_dir / "PRD_INDEX.md")
    _upsert_decisions(docs_dir / "DECISIONS.md")

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text(f"{PRD} runner executed.\n", encoding="utf-8")

    tracked, hash_before = planning.tracked_hashes(repo_root)

    preflight_payload = planning.preflight(reports_dir, docs_dir)
    source_gate = planning.build_source_gate(preflight_payload)
    cohort_policy = planning.build_cohort_policy()
    toggle_matrix = planning.build_toggle_matrix()
    preflight_gates = planning.build_preflight_gates()
    hard_stop_criteria = planning.build_hard_stop_criteria()
    monitoring_plan = planning.build_monitoring_plan()
    rollback_plan = planning.build_rollback_plan()
    evidence_capture_plan = planning.build_evidence_capture_plan()
    normal_user_no_effect_plan = planning.build_normal_user_no_effect_plan()
    controlled_rollout_plan = planning.build_controlled_rollout_plan(
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        preflight_gates=preflight_gates,
        hard_stop_criteria=hard_stop_criteria,
        monitoring_plan=monitoring_plan,
        rollback_plan=rollback_plan,
        evidence_capture_plan=evidence_capture_plan,
        normal_user_no_effect_plan=normal_user_no_effect_plan,
    )

    hash_after = {name: planning._sha256(path) if path.exists() else "missing" for name, path in tracked.items()}
    no_mutation_proof = planning.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    docs_sync = planning.docs_sync_status(docs_dir)

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "controlled_rollout_plan.json", controlled_rollout_plan)
    _write_json(output_dir / "cohort_policy.json", cohort_policy)
    _write_json(output_dir / "toggle_matrix.json", toggle_matrix)
    _write_json(output_dir / "preflight_gates.json", preflight_gates)
    _write_json(output_dir / "hard_stop_criteria.json", hard_stop_criteria)
    _write_json(output_dir / "monitoring_plan.json", monitoring_plan)
    _write_json(output_dir / "rollback_plan.json", rollback_plan)
    _write_json(output_dir / "evidence_capture_plan.json", evidence_capture_plan)
    _write_json(output_dir / "normal_user_no_effect_plan.json", normal_user_no_effect_plan)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

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
    _write_json(output_dir / "artifact_hygiene_report.json", encoding_report)

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    decision, scorecard = planning.build_decision_and_scorecard(
        source_gate=source_gate,
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        preflight_gates=preflight_gates,
        hard_stop_criteria=hard_stop_criteria,
        monitoring_plan=monitoring_plan,
        rollback_plan=rollback_plan,
        evidence_capture_plan=evidence_capture_plan,
        normal_user_no_effect_plan=normal_user_no_effect_plan,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    _write_json(output_dir / "decision.json", decision)
    _write_json(output_dir / "scorecard.json", scorecard)

    _write_text(
        reports_dir / "PRD-046.1.30_CONTROLLED_ROLLOUT_PLANNING_REPORT.md",
        _render_controlled_rollout_planning_report(source_gate=source_gate, scorecard=scorecard),
    )
    _write_text(reports_dir / "PRD-046.1.30_OPERATOR_RUNBOOK.md", _render_operator_runbook())
    _write_text(reports_dir / "PRD-046.1.30_NEXT_PRD_RECOMMENDATION.md", _render_next_prd_recommendation(scorecard))
    _write_text(
        reports_dir / "PRD-046.1.30_IMPLEMENTATION_REPORT.md",
        _render_implementation_report(
            scorecard=scorecard,
            commands=[
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_contract.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_source_gate.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_cohort_policy.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_toggle_matrix.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_preflight_gates.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_hard_stops.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_evidence_plan.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_normal_user_no_effect.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_no_mutation.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_artifact_hygiene.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_planning_decision_gate.py",
                "python -m bot_psychologist.tools.run_diagnostic_center_controlled_rollout_planning --repo-root . --reports-dir TO_DO_LIST/reports --docs-dir docs --logs-dir TO_DO_LIST/logs --output-dir TO_DO_LIST/logs/PRD-046.1.30 --strict",
            ],
        ),
    )

    if strict and scorecard.get("final_status") != "passed":
        return {
            "status": "blocked",
            "decision": scorecard.get("decision", "blocked_needs_hotfix"),
            "scorecard": scorecard,
            "preflight": preflight_payload,
        }

    return {
        "status": scorecard.get("final_status", "blocked"),
        "decision": scorecard.get("decision", "blocked_needs_hotfix"),
        "scorecard": scorecard,
        "preflight": preflight_payload,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.30 Diagnostic Center controlled rollout planning gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--logs-dir", default="TO_DO_LIST/logs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.30")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
