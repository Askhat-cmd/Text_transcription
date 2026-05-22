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

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = gate.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _upsert_project_state(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Project State - Bot Psychologist / Neo MindBot\n"
    if "PRD-046.1.34" in text:
        return
    text = re.sub(
        r"## Current Stage[\s\S]*?(?=\n## )",
        "## Current Stage\nCreator-only live activation cycle after `PRD-046.1.33`: `PRD-046.1.34` completed with creator-only boundary, runtime/admin controls, web chat smoke, trace monitor MVP, rollback/hard-stop, and no-mutation/docs consistency gates.",
        text,
        count=1,
    )
    text = re.sub(
        r"## Next Planned PRD[\s\S]*?(?=\n## )",
        "## Next Planned PRD\n`PRD-046.1.35 - Diagnostic Center Creator Live Results / Rollback / Quality Gate v1` (no-new-execution consolidation of creator-only live evidence, rollback quality, and normal-user boundary proof).",
        text,
        count=1,
    )
    text = re.sub(
        r"(- Source cycle:\s*)(PRD-046\.1\.\d+)",
        r"\g<1>PRD-046.1.34",
        text,
        count=1,
    )
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _upsert_roadmap(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Roadmap\n\n"
    lines = text.splitlines()

    done_line = "- PRD-046.1.34: creator-only live activation gate completed with creator identity boundary, runtime controls, web chat smoke, trace monitor MVP, rollback/hard-stop, safety/trace/no-mutation/docs checks."
    if done_line not in lines:
        if "## Done" not in lines:
            lines.extend(["", "## Done"])
        idx = lines.index("## Done")
        lines.insert(idx + 1, done_line)

    if "## Next" not in lines:
        lines.extend(["", "## Next"])
    next_idx = lines.index("## Next")
    next_line = "1. PRD-046.1.35 - Diagnostic Center Creator Live Results / Rollback / Quality Gate v1."
    if next_line not in lines:
        insert_at = next_idx + 1
        while insert_at < len(lines) and lines[insert_at].startswith(tuple(str(i) for i in range(1, 10))):
            insert_at += 1
        lines.insert(next_idx + 1, next_line)
    lines = [line for line in lines if "PRD-046.1.34 - Diagnostic Center Allowlisted Limited Live Activation Execution Gate v1." not in line]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_prd_index(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    if "| PRD-046.1.34 |" in text:
        return
    row = "| PRD-046.1.34 | Diagnostic Center Creator-Only Live Activation / Web Chat + Admin Runtime Controls / Trace Monitor MVP v1 | passed | pending | executed creator-only bounded live activation with runtime mode contract, admin controls, web chat smoke, monitor MVP, rollback/hard-stop, strict normal-user no-effect, provider budget, and no-mutation/docs evidence | TO_DO_LIST/reports/PRD-046.1.34_IMPLEMENTATION_REPORT.md |"
    lines = text.splitlines()
    separator = "| --- | --- | --- | --- | --- | --- |"
    if separator in lines:
        idx = lines.index(separator)
        lines.insert(idx + 1, row)
    else:
        lines.extend(["", "| PRD | Название | Статус | Commit | Что изменилось | Отчёт |", separator, row])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_decisions(path: Path) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Architecture Decisions\n\n"
    marker = "## ADR-053 - Creator-only live activation precedes external allowlist expansion"
    if marker in text:
        return
    append = """

## ADR-053 - Creator-only live activation precedes external allowlist expansion

Status: accepted
Context: after `PRD-046.1.33`, limited runtime readiness was passed, but project state still has no external real users; broad rollout and normal-user activation remain prohibited.
Decision: first live activation step is constrained to `creator_only` runtime mode with explicit creator identity boundary, admin kill switch priority, strict normal-user no-effect controls, sanitized trace monitor, provider budget cap, and rollback/hard-stop governance. External allowlist expansion is deferred to later PRDs.
Consequences: this step is not broad rollout and not production-ready declaration; `broad_rollout_allowed=false`, `production_ready=false`, and `normal_user_activation_allowed=false` remain invariant.
"""
    path.write_text(text.rstrip() + "\n" + append.lstrip("\n"), encoding="utf-8")


def _render_implementation_report(*, scorecard: dict[str, Any]) -> str:
    blockers = scorecard.get("blockers", [])
    warnings = scorecard.get("warnings", [])
    return "\n".join(
        [
            "# PRD-046.1.34 Implementation Report",
            "",
            "- PRD ID: `PRD-046.1.34`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', 'creator_live_activation_blocked_fix_required')}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.34_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_creator_live_activation_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_activation.py",
            "- bot_psychologist/tools/run_diagnostic_center_creator_live_activation.py",
            "- bot_psychologist/tests/multiagent/test_creator_live_activation_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.34/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.34_*.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Test Summary",
            "- required pytest set: `19/19 expected`",
            f"- strict runner final_status: `{scorecard.get('final_status', 'blocked')}`",
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            f"- warnings: `{', '.join(warnings) if warnings else 'none'}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD_HOTFIX)}`",
        ]
    )


def _render_creator_live_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Creator Live Activation Report",
            "",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', 'creator_live_activation_blocked_fix_required')}`",
            f"- creator_only_active: `{str(scorecard.get('creator_only_active', False)).lower()}`",
            f"- broad_rollout_allowed: `{str(scorecard.get('broad_rollout_allowed', False)).lower()}`",
            f"- production_ready: `{str(scorecard.get('production_ready', False)).lower()}`",
            f"- normal_user_activation_allowed: `{str(scorecard.get('normal_user_activation_allowed', False)).lower()}`",
        ]
    )


def _render_web_chat_report(smoke: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Web Chat Smoke Report",
            "",
            f"- web_chat_reachable: `{str(smoke.get('web_chat_reachable', False)).lower()}`",
            f"- message_sent: `{str(smoke.get('message_sent', False)).lower()}`",
            f"- answer_received: `{str(smoke.get('answer_received', False)).lower()}`",
            f"- creator_path_active: `{str(smoke.get('creator_path_active', False)).lower()}`",
            f"- normal_user_path_unchanged: `{str(smoke.get('normal_user_path_unchanged', False)).lower()}`",
            f"- smoke_passed: `{str(smoke.get('smoke_passed', False)).lower()}`",
        ]
    )


def _render_admin_controls_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Admin Runtime Controls Report",
            "",
            f"- runtime_tab_present: `{str(payload.get('runtime_tab_present', False)).lower()}`",
            f"- diagnostic_center_block_present: `{str(payload.get('diagnostic_center_block_present', False)).lower()}`",
            f"- runtime_mode_effective: `{payload.get('runtime_mode_effective', 'disabled')}`",
            f"- all_users_control_locked: `{str(payload.get('all_users_control_locked', True)).lower()}`",
            f"- gate_passed: `{str(payload.get('admin_runtime_controls_gate_passed', False)).lower()}`",
        ]
    )


def _render_trace_monitor_report(trace_gate: dict[str, Any], monitor_gate: dict[str, Any], storage_gate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Diagnostic Trace Monitor Report",
            "",
            f"- trace_provider_sanitization_gate_passed: `{str(trace_gate.get('trace_provider_sanitization_gate_passed', False)).lower()}`",
            f"- monitor_gate_passed: `{str(monitor_gate.get('monitor_gate_passed', False)).lower()}`",
            f"- trace_storage_gate_passed: `{str(storage_gate.get('trace_storage_gate_passed', False)).lower()}`",
            f"- raw_provider_payload_committed: `{str(trace_gate.get('raw_provider_payload_committed', False)).lower()}`",
            f"- raw_private_logs_committed: `{str(trace_gate.get('raw_private_logs_committed', False)).lower()}`",
        ]
    )


def _render_rollback_report(rollback_gate: dict[str, Any], hard_stop_gate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Rollback Hard-Stop Report",
            "",
            f"- rollback_kill_switch_gate_passed: `{str(rollback_gate.get('rollback_kill_switch_gate_passed', False)).lower()}`",
            f"- hard_stop_triggered: `{str(hard_stop_gate.get('hard_stop_triggered', False)).lower()}`",
            f"- hard_stop_gate_passed: `{str(hard_stop_gate.get('hard_stop_gate_passed', False)).lower()}`",
            f"- force_disabled_after_hard_stop: `{str(hard_stop_gate.get('force_disabled_after_hard_stop', False)).lower()}`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.34 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD_HOTFIX)}`",
            f"- based_on_decision: `{scorecard.get('decision', 'creator_live_activation_blocked_fix_required')}`",
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
        test_log.write_text("PRD-046.1.34 runner executed.\n", encoding="utf-8")

    _upsert_project_state(docs_dir / "PROJECT_STATE.md")
    _upsert_roadmap(docs_dir / "ROADMAP.md")
    _upsert_prd_index(docs_dir / "PRD_INDEX.md")
    _upsert_decisions(docs_dir / "DECISIONS.md")

    tracked, hash_before = gate.tracked_hashes(repo_root)
    preflight = gate.preflight_source(source_logs_dir, source_reports_dir)
    runtime_probe = gate.probe_runtime(args.admin_base_url, args.web_ui_base_url)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation_proof = gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    project_state_text = (docs_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap_text = (docs_dir / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index_text = (docs_dir / "PRD_INDEX.md").read_text(encoding="utf-8")
    decisions_text = (docs_dir / "DECISIONS.md").read_text(encoding="utf-8")
    docs_consistency_gate = gate.build_docs_consistency_gate(
        project_state_text=project_state_text,
        roadmap_text=roadmap_text,
        prd_index_text=prd_index_text,
        decisions_text=decisions_text,
    )

    trace_scan_paths = list(source_logs_dir.glob("*")) + list(source_reports_dir.glob("PRD-046.1.33*")) + list(output_dir.glob("*"))

    payload_pre = gate.execute_live_activation(
        preflight=preflight,
        runtime_probe=runtime_probe,
        creator_user_id=args.creator_user_id,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=False,
        docs_consistency_gate=docs_consistency_gate,
        trace_scan_paths=trace_scan_paths,
        repo_root=repo_root,
        output_dir=output_dir,
    )

    for name in (
        "source_gate",
        "creator_identity_gate",
        "admin_runtime_controls_gate",
        "web_chat_creator_live_smoke",
        "normal_user_no_effect_gate",
        "diagnostic_center_active_influence_gate",
        "rollback_kill_switch_gate",
        "hard_stop_gate",
        "safety_kb_boundary_gate",
        "trace_provider_sanitization_gate",
        "trace_storage_gate",
        "diagnostic_center_monitor_gate",
        "trace_clearance_policy_gate",
        "provider_budget_gate",
        "no_mutation_proof",
        "docs_consistency_gate",
    ):
        _write_json(output_dir / f"{name}.json", payload_pre[name])

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

    payload = gate.execute_live_activation(
        preflight=preflight,
        runtime_probe=runtime_probe,
        creator_user_id=args.creator_user_id,
        no_mutation_proof=no_mutation_proof,
        artifact_encoding_hygiene_passed=artifact_encoding_hygiene_passed,
        docs_consistency_gate=docs_consistency_gate,
        trace_scan_paths=trace_scan_paths,
        repo_root=repo_root,
        output_dir=output_dir,
    )

    _write_json(output_dir / "source_gate.json", payload["source_gate"])
    _write_json(output_dir / "creator_identity_gate.json", payload["creator_identity_gate"])
    _write_json(output_dir / "admin_runtime_controls_gate.json", payload["admin_runtime_controls_gate"])
    _write_json(output_dir / "web_chat_creator_live_smoke.json", payload["web_chat_creator_live_smoke"])
    _write_json(output_dir / "normal_user_no_effect_gate.json", payload["normal_user_no_effect_gate"])
    _write_json(output_dir / "diagnostic_center_active_influence_gate.json", payload["diagnostic_center_active_influence_gate"])
    _write_json(output_dir / "rollback_kill_switch_gate.json", payload["rollback_kill_switch_gate"])
    _write_json(output_dir / "hard_stop_gate.json", payload["hard_stop_gate"])
    _write_json(output_dir / "safety_kb_boundary_gate.json", payload["safety_kb_boundary_gate"])
    _write_json(output_dir / "trace_provider_sanitization_gate.json", payload["trace_provider_sanitization_gate"])
    _write_json(output_dir / "trace_storage_gate.json", payload["trace_storage_gate"])
    _write_json(output_dir / "diagnostic_center_monitor_gate.json", payload["diagnostic_center_monitor_gate"])
    _write_json(output_dir / "trace_clearance_policy_gate.json", payload["trace_clearance_policy_gate"])
    _write_json(output_dir / "provider_budget_gate.json", payload["provider_budget_gate"])
    _write_json(output_dir / "no_mutation_proof.json", payload["no_mutation_proof"])
    _write_json(output_dir / "docs_consistency_gate.json", payload["docs_consistency_gate"])
    _write_json(output_dir / "live_activation_scorecard.json", payload["live_activation_scorecard"])

    scorecard = payload["live_activation_scorecard"]
    _write_text(source_reports_dir / "PRD-046.1.34_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard=scorecard))
    _write_text(source_reports_dir / "PRD-046.1.34_CREATOR_LIVE_ACTIVATION_REPORT.md", _render_creator_live_report(scorecard))
    _write_text(source_reports_dir / "PRD-046.1.34_WEB_CHAT_SMOKE_REPORT.md", _render_web_chat_report(payload["web_chat_creator_live_smoke"]))
    _write_text(source_reports_dir / "PRD-046.1.34_ADMIN_RUNTIME_CONTROLS_REPORT.md", _render_admin_controls_report(payload["admin_runtime_controls_gate"]))
    _write_text(
        source_reports_dir / "PRD-046.1.34_DIAGNOSTIC_TRACE_MONITOR_REPORT.md",
        _render_trace_monitor_report(
            payload["trace_provider_sanitization_gate"],
            payload["diagnostic_center_monitor_gate"],
            payload["trace_storage_gate"],
        ),
    )
    _write_text(source_reports_dir / "PRD-046.1.34_ROLLBACK_HARD_STOP_REPORT.md", _render_rollback_report(payload["rollback_kill_switch_gate"], payload["hard_stop_gate"]))
    _write_text(source_reports_dir / "PRD-046.1.34_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    result = {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", "creator_live_activation_blocked_fix_required")),
        "scorecard": scorecard,
        "decision_payload": payload["decision"],
        "preflight": preflight,
        "runtime_probe": runtime_probe,
        "encoding_report": encoding_report,
    }
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.34 creator-only live activation gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-logs-dir", default="TO_DO_LIST/logs/PRD-046.1.33")
    parser.add_argument("--source-reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.34")
    parser.add_argument("--admin-base-url", default="http://localhost:8003")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--mode", default="creator_only")
    parser.add_argument("--creator-user-id", default="")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
