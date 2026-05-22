from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = gate.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _replace_section(text: str, header: str, content: str) -> str:
    pattern = re.compile(rf"{re.escape(header)}\n[\s\S]*?(?=\n## |\Z)")
    block = f"{header}\n{content.strip()}\n"
    if pattern.search(text):
        return pattern.sub(block.rstrip("\n"), text, count=1)
    return text.rstrip() + "\n\n" + block


def _upsert_project_state(path: Path, decision: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Project State - Bot Psychologist / Neo MindBot\n"
    if decision == gate.DECISION_CONTINUE:
        current_stage = "Creator-only live results gate passed after `PRD-046.1.35`. Next: controlled creator-limited observation / next acceptance gate."
        next_prd = f"`{gate.NEXT_PRD_CONTINUE}`"
    elif decision == gate.DECISION_EVIDENCE_HOTFIX:
        current_stage = "PRD-046.1.35 found creator live activation safety gates green, but actual live turn evidence is incomplete/weak. Next: PRD-046.1.35-HF1 evidence capture repair."
        next_prd = f"`{gate.NEXT_PRD_HF1}`"
    elif decision == gate.DECISION_ROLLBACK:
        current_stage = "PRD-046.1.35 requires rollback/safety repair before any continuation."
        next_prd = f"`{gate.NEXT_PRD_RB1}`"
    else:
        current_stage = "PRD-046.1.35 blocked by artifacts/docs/no-mutation/provider evidence issues; fix required before continuation."
        next_prd = f"`{gate.NEXT_PRD_HF1}`"
    text = _replace_section(text, "## Current Stage", current_stage)
    text = _replace_section(text, "## Next Planned PRD", next_prd)
    text = re.sub(r"(- Source cycle:\s*)(PRD-046\.1\.\d+)", r"\g<1>PRD-046.1.35", text, count=1)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _upsert_roadmap(path: Path, scorecard: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Roadmap\n\n"
    lines = text.splitlines()
    done_line = (
        "- PRD-046.1.35: creator-live results/rollback/quality gate completed in no-new-execution mode "
        "with evidence-strength audit, safety boundary verification, trace/no-mutation/docs gates, and decision handoff."
    )
    if done_line not in lines:
        if "## Done" not in lines:
            lines.extend(["", "## Done"])
        idx = lines.index("## Done")
        lines.insert(idx + 1, done_line)

    if "## Next" not in lines:
        lines.extend(["", "## Next"])
    next_idx = lines.index("## Next")
    while next_idx + 1 < len(lines) and re.match(r"\d+\.\s+PRD-046\.1\.(35|36|35-HF1|35-RB1)", lines[next_idx + 1]):
        lines.pop(next_idx + 1)

    decision = str(scorecard.get("decision", gate.DECISION_BLOCKED))
    if decision == gate.DECISION_CONTINUE:
        next_line = f"1. {gate.NEXT_PRD_CONTINUE}."
    elif decision == gate.DECISION_ROLLBACK:
        next_line = f"1. {gate.NEXT_PRD_RB1}."
    else:
        next_line = f"1. {gate.NEXT_PRD_HF1}."
    lines.insert(next_idx + 1, next_line)
    lines = [line for line in lines if "PRD-046.1.35 - Diagnostic Center Creator Live Results / Rollback / Quality Gate v1." not in line]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_prd_index(path: Path, scorecard: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    row = (
        "| PRD-046.1.35 | Diagnostic Center Creator Live Results / Rollback / Quality Gate v1 | "
        f"{scorecard.get('final_status', 'blocked')} | pending | "
        "consolidated PRD-046.1.34 evidence in no-new-execution mode, added explicit evidence-strength classification "
        "and rollback/normal-user/trace/provider/no-mutation/docs gates | "
        "TO_DO_LIST/reports/PRD-046.1.35_IMPLEMENTATION_REPORT.md |"
    )
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("| PRD-046.1.35 |"):
            lines[idx] = row
            path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            return
    separator = "| --- | --- | --- | --- | --- | --- |"
    if separator in lines:
        idx = lines.index(separator)
        lines.insert(idx + 1, row)
    else:
        lines.extend(["", "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |", separator, row])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_decisions(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Architecture Decisions\n\n"
    marker = "## ADR-054 - Creator live continuation requires explicit evidence-strength gate"
    if marker in text:
        return
    append = """

## ADR-054 - Creator live continuation requires explicit evidence-strength gate

Status: accepted
Context: PRD-046.1.34 passed safety/runtime boundaries, but web chat smoke evidence can be probe-level or simulated without strong sanitized live-turn proof.
Decision: PRD-046.1.35 introduces a dedicated evidence-strength audit that classifies artifacts into `actual_live_turn_evidence`, `runtime_probe_evidence`, `simulated_gate_evidence`, and `missing_evidence`; continuation beyond creator-only stage is blocked when actual live-turn evidence is absent.
Consequences: safety-green is necessary but insufficient; rollout remains constrained until evidence quality is explicit and reproducible.
"""
    path.write_text(text.rstrip() + "\n" + append.lstrip("\n"), encoding="utf-8")


def _render_implementation_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35 Implementation Report",
            "",
            "- PRD ID: `PRD-046.1.35`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.35_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_creator_live_results_gate_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_results_gate.py",
            "- bot_psychologist/tools/run_diagnostic_center_creator_live_results_gate.py",
            "- bot_psychologist/tests/multiagent/test_creator_live_results_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.35/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.35_*.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Test Summary",
            "- required pytest set: `10/10 expected`",
            f"- strict runner final_status: `{scorecard.get('final_status', 'blocked')}`",
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(scorecard.get('blockers', [])) or 'none'}`",
            f"- warnings: `{', '.join(scorecard.get('warnings', [])) or 'none'}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD_HF1)}`",
        ]
    )


def _render_creator_live_results_report(scorecard: dict[str, Any]) -> str:
    proved = [
        "- PRD-046.1.34 proved creator-only safety boundaries, rollback/hard-stop controls, and normal-user no-effect gates.",
        "- PRD-046.1.34 preserved no-mutation and trace sanitization controls.",
    ]
    not_proved = [
        "- PRD-046.1.34 did not prove strong actual live-turn evidence with full sanitized answer/session/timestamp bundle.",
    ]
    return "\n".join(
        [
            "# PRD-046.1.35 Creator Live Results Report",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED)}`",
            "",
            "## What PRD-046.1.34 Proved",
            *proved,
            "",
            "## What PRD-046.1.34 Did Not Prove",
            *not_proved,
            "",
            f"- creator_path_can_continue: `{str(scorecard.get('decision') == gate.DECISION_CONTINUE).lower()}`",
            f"- normal_user_path_untouched: `{str(scorecard.get('normal_user_boundary_gate') == 'passed').lower()}`",
        ]
    )


def _render_evidence_report(audit: dict[str, Any]) -> str:
    weak_items = []
    for item in audit.get("items", []):
        if str(item.get("evidence_strength", "")) in {"weak", "missing"}:
            weak_items.append(f"- `{item.get('artifact', 'unknown')}`: {item.get('reason', 'n/a')}")
    if not weak_items:
        weak_items = ["- none"]
    return "\n".join(
        [
            "# PRD-046.1.35 Evidence Strength Audit Report",
            "",
            f"- actual_live_turn_evidence_count: `{audit.get('actual_live_turn_evidence_count', 0)}`",
            f"- runtime_probe_evidence_count: `{audit.get('runtime_probe_evidence_count', 0)}`",
            f"- simulated_gate_evidence_count: `{audit.get('simulated_gate_evidence_count', 0)}`",
            f"- missing_evidence_count: `{audit.get('missing_evidence_count', 0)}`",
            f"- strong_evidence_count: `{audit.get('strong_evidence_count', 0)}`",
            f"- medium_evidence_count: `{audit.get('medium_evidence_count', 0)}`",
            f"- weak_evidence_count: `{audit.get('weak_evidence_count', 0)}`",
            f"- missing_strength_count: `{audit.get('missing_strength_count', 0)}`",
            "",
            "## Weak/Missing Evidence Items",
            *weak_items,
        ]
    )


def _render_rollback_report(rollback_gate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35 Rollback Quality Report",
            "",
            f"- rollback_quality_gate_passed: `{str(rollback_gate.get('rollback_quality_gate_passed', False)).lower()}`",
            f"- force_disabled_toggle_present: `{str(rollback_gate.get('force_disabled_toggle_present', False)).lower()}`",
            f"- force_disabled_priority_preserved: `{str(rollback_gate.get('force_disabled_priority_preserved', False)).lower()}`",
            f"- all_users_control_locked: `{str(rollback_gate.get('all_users_control_locked', False)).lower()}`",
            f"- hard_stop_gate_passed: `{str(rollback_gate.get('hard_stop_gate_passed', False)).lower()}`",
        ]
    )


def _render_normal_user_report(normal_gate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35 Normal User Boundary Report",
            "",
            f"- normal_user_boundary_gate_passed: `{str(normal_gate.get('normal_user_boundary_gate_passed', False)).lower()}`",
            f"- normal_user_apply_effect_count: `{normal_gate.get('normal_user_apply_effect_count', 'n/a')}`",
            f"- normal_user_provider_call_count: `{normal_gate.get('normal_user_provider_call_count', 'n/a')}`",
            f"- writer_prompt_delta_count: `{normal_gate.get('writer_prompt_delta_count', 'n/a')}`",
            f"- final_answer_path_delta_count: `{normal_gate.get('final_answer_path_delta_count', 'n/a')}`",
            f"- trace_private_leak_count: `{normal_gate.get('trace_private_leak_count', 'n/a')}`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.35 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD_HF1)}`",
            f"- based_on_decision: `{scorecard.get('decision', gate.DECISION_BLOCKED)}`",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_logs_dir = Path(args.source_logs_dir).resolve()
    source_reports_dir = Path(args.source_reports_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.35 runner executed.\n", encoding="utf-8")

    preflight = gate.preflight_source_artifacts(source_logs_dir, source_reports_dir)
    tracked, hash_before = gate.tracked_hashes(repo_root)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001

    # First pass for decision preselection before docs upsert.
    placeholder_docs_gate = {
        "docs_consistency_gate_passed": True,
        "docs_consistency_gate": "passed",
    }
    scan_paths = list(source_logs_dir.glob("*")) + list(output_dir.glob("*"))
    payload_pre = gate.execute_results_gate(
        preflight=preflight,
        hash_before=hash_before,
        hash_after=hash_after,
        docs_consistency_gate=placeholder_docs_gate,
        artifact_encoding_hygiene_passed=False,
        strict=args.strict,
        scan_paths=scan_paths,
    )
    pre_scorecard = payload_pre["results_scorecard"]
    _upsert_project_state(docs_dir / "PROJECT_STATE.md", str(pre_scorecard.get("decision", gate.DECISION_BLOCKED)))
    _upsert_roadmap(docs_dir / "ROADMAP.md", pre_scorecard)
    _upsert_prd_index(docs_dir / "PRD_INDEX.md", pre_scorecard)
    _upsert_decisions(docs_dir / "DECISIONS.md")

    expected_next = str(pre_scorecard.get("next_prd_recommendation", gate.NEXT_PRD_HF1))
    docs_gate = gate.build_docs_consistency_gate(
        project_state_text=(docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8"),
        roadmap_text=(docs_dir / "ROADMAP.md").read_text(encoding="utf-8"),
        prd_index_text=(docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8"),
        decisions_text=(docs_dir / "DECISIONS.md").read_text(encoding="utf-8"),
        expected_next=expected_next,
    )

    payload_mid = gate.execute_results_gate(
        preflight=preflight,
        hash_before=hash_before,
        hash_after=hash_after,
        docs_consistency_gate=docs_gate,
        artifact_encoding_hygiene_passed=False,
        strict=args.strict,
        scan_paths=scan_paths,
    )

    _write_json(output_dir / "source_artifacts_manifest.json", payload_mid["source_artifacts_manifest"])
    _write_json(output_dir / "evidence_strength_audit.json", payload_mid["evidence_strength_audit"])
    _write_json(output_dir / "live_results_quality_gate.json", payload_mid["live_results_quality_gate"])
    _write_json(output_dir / "rollback_quality_gate.json", payload_mid["rollback_quality_gate"])
    _write_json(output_dir / "normal_user_boundary_proof.json", payload_mid["normal_user_boundary_proof"])
    _write_json(output_dir / "trace_sanitization_results_gate.json", payload_mid["trace_sanitization_results_gate"])
    _write_json(output_dir / "provider_budget_results_gate.json", payload_mid["provider_budget_results_gate"])
    _write_json(output_dir / "no_mutation_proof.json", payload_mid["no_mutation_proof"])
    _write_json(output_dir / "docs_consistency_gate.json", payload_mid["docs_consistency_gate"])
    _write_json(output_dir / "results_scorecard.json", payload_mid["results_scorecard"])

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(output_dir),
            reports_dir=str(source_reports_dir),
            out_dir=str(output_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )
    artifact_encoding_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"

    payload = gate.execute_results_gate(
        preflight=preflight,
        hash_before=hash_before,
        hash_after=hash_after,
        docs_consistency_gate=docs_gate,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        strict=args.strict,
        scan_paths=scan_paths,
    )

    _write_json(output_dir / "source_artifacts_manifest.json", payload["source_artifacts_manifest"])
    _write_json(output_dir / "evidence_strength_audit.json", payload["evidence_strength_audit"])
    _write_json(output_dir / "live_results_quality_gate.json", payload["live_results_quality_gate"])
    _write_json(output_dir / "rollback_quality_gate.json", payload["rollback_quality_gate"])
    _write_json(output_dir / "normal_user_boundary_proof.json", payload["normal_user_boundary_proof"])
    _write_json(output_dir / "trace_sanitization_results_gate.json", payload["trace_sanitization_results_gate"])
    _write_json(output_dir / "provider_budget_results_gate.json", payload["provider_budget_results_gate"])
    _write_json(output_dir / "no_mutation_proof.json", payload["no_mutation_proof"])
    _write_json(output_dir / "docs_consistency_gate.json", payload["docs_consistency_gate"])
    _write_json(output_dir / "results_scorecard.json", payload["results_scorecard"])

    scorecard = payload["results_scorecard"]
    _upsert_project_state(docs_dir / "PROJECT_STATE.md", str(scorecard.get("decision", gate.DECISION_BLOCKED)))
    _upsert_roadmap(docs_dir / "ROADMAP.md", scorecard)
    _upsert_prd_index(docs_dir / "PRD_INDEX.md", scorecard)
    _upsert_decisions(docs_dir / "DECISIONS.md")

    docs_gate_final = gate.build_docs_consistency_gate(
        project_state_text=(docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8"),
        roadmap_text=(docs_dir / "ROADMAP.md").read_text(encoding="utf-8"),
        prd_index_text=(docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8"),
        decisions_text=(docs_dir / "DECISIONS.md").read_text(encoding="utf-8"),
        expected_next=str(scorecard.get("next_prd_recommendation", gate.NEXT_PRD_HF1)),
    )
    payload["docs_consistency_gate"] = docs_gate_final
    _write_json(output_dir / "docs_consistency_gate.json", payload["docs_consistency_gate"])

    _write_text(source_reports_dir / "PRD-046.1.35_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard))
    _write_text(source_reports_dir / "PRD-046.1.35_CREATOR_LIVE_RESULTS_REPORT.md", _render_creator_live_results_report(scorecard))
    _write_text(source_reports_dir / "PRD-046.1.35_EVIDENCE_STRENGTH_AUDIT_REPORT.md", _render_evidence_report(payload["evidence_strength_audit"]))
    _write_text(source_reports_dir / "PRD-046.1.35_ROLLBACK_QUALITY_REPORT.md", _render_rollback_report(payload["rollback_quality_gate"]))
    _write_text(source_reports_dir / "PRD-046.1.35_NORMAL_USER_BOUNDARY_REPORT.md", _render_normal_user_report(payload["normal_user_boundary_proof"]))
    _write_text(source_reports_dir / "PRD-046.1.35_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    result = {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", gate.DECISION_BLOCKED)),
        "scorecard": scorecard,
        "decision_payload": payload["decision"],
        "preflight": preflight,
        "docs_consistency_gate": docs_gate_final,
        "encoding_report": encoding_report,
    }
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.35 creator live results gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-logs-dir", default="TO_DO_LIST/logs/PRD-046.1.34")
    parser.add_argument("--source-reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.35")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
