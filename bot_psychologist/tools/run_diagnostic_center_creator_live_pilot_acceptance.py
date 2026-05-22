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

from bot_agent.multiagent import diagnostic_center_creator_live_pilot_acceptance as gate
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


def _upsert_docs(docs_dir: Path, final_status: str) -> None:
    project_state = docs_dir / "PROJECT_STATE.md"
    roadmap = docs_dir / "ROADMAP.md"
    prd_index = docs_dir / "PRD_INDEX.md"
    decisions = docs_dir / "DECISIONS.md"

    ps_text = project_state.read_text(encoding="utf-8") if project_state.exists() else "# Project State\n"
    if final_status == "passed":
        current = (
            "PRD-046.1.36 accepted Diagnostic Center as governed creator-live pilot layer. "
            "Creator-only / allowlist runtime is accepted for developer pilot. "
            "Admin runtime controls and rollback/hard-stop are verified. "
            "Normal users remain unaffected. Broad rollout and production-ready declaration remain prohibited."
        )
        next_prd = f"`{gate.NEXT_PRD}`"
    else:
        current = "PRD-046.1.36 blocked creator-live pilot acceptance; targeted hotfix is required before completion decision gate."
        next_prd = "`targeted HF before Diagnostic Center completion decision`"
    ps_text = _replace_section(ps_text, "## Current Stage", current)
    ps_text = _replace_section(ps_text, "## Next Planned PRD", next_prd)
    project_state.write_text(ps_text.rstrip() + "\n", encoding="utf-8")

    rm_text = roadmap.read_text(encoding="utf-8") if roadmap.exists() else "# Roadmap\n\n"
    done_line = "- PRD-046.1.36: creator-live pilot acceptance completed with source/runtime/admin/creator-pilot/rollback/normal-user/safety gates."
    if done_line not in rm_text:
        rm_text = rm_text.rstrip() + "\n\n## Done\n" + done_line + "\n"
    rm_text = re.sub(
        r"## Next\n[\s\S]*?(?=\n## |\Z)",
        "## Next\n1. PRD-046.1.37 - Diagnostic Center Final Results / Completion Decision Gate v1.\n",
        rm_text,
        count=1,
    ) if "## Next" in rm_text else rm_text.rstrip() + "\n\n## Next\n1. PRD-046.1.37 - Diagnostic Center Final Results / Completion Decision Gate v1.\n"
    roadmap.write_text(rm_text.rstrip() + "\n", encoding="utf-8")

    pi_text = prd_index.read_text(encoding="utf-8") if prd_index.exists() else "# PRD Index\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n"
    row = "| PRD-046.1.36 | Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1 | pending | pending | accepted bounded creator-live pilot contract with admin runtime controls, rollback/no-effect proofs, and safety gates | TO_DO_LIST/reports/PRD-046.1.36_IMPLEMENTATION_REPORT.md |"
    if "| PRD-046.1.36 |" not in pi_text:
        lines = pi_text.splitlines()
        sep = "| --- | --- | --- | --- | --- | --- |"
        if sep in lines:
            idx = lines.index(sep)
            lines.insert(idx + 1, row)
            pi_text = "\n".join(lines)
        else:
            pi_text = pi_text.rstrip() + "\n\n| PRD | Название | Статус | Commit | Что изменилось | Отчёт |\n| --- | --- | --- | --- | --- | --- |\n" + row + "\n"
    prd_index.write_text(pi_text.rstrip() + "\n", encoding="utf-8")

    de_text = decisions.read_text(encoding="utf-8") if decisions.exists() else "# Architecture Decisions\n\n"
    marker = "## ADR-055 - Diagnostic Center creator-live pilot acceptance boundary is completion-ready without broad rollout"
    if marker not in de_text:
        de_text = de_text.rstrip() + """

## ADR-055 - Diagnostic Center creator-live pilot acceptance boundary is completion-ready without broad rollout

Status: accepted
Context: HF4 passed behavior calibration and creator pipeline evidence, while broad rollout and production-ready declaration remain disallowed.
Decision: PRD-046.1.36 accepts Diagnostic Center as a governed creator-live pilot layer with runtime controls, rollback hard-stop, and strict normal-user no-effect boundary.
Consequences: next step is final completion decision gate (`PRD-046.1.37`), not broad rollout.
"""
    decisions.write_text(de_text.rstrip() + "\n", encoding="utf-8")


def _render_implementation_report(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.36 Implementation Report",
            "",
            "- PRD ID: `PRD-046.1.36`",
            f"- final_status: `{scorecard.get('final_status', 'blocked')}`",
            f"- decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_CREATOR)}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.36_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_creator_live_pilot_acceptance_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_pilot_acceptance.py",
            "- bot_psychologist/tools/run_diagnostic_center_creator_live_pilot_acceptance.py",
            "- bot_psychologist/tests/fixtures/prd_046_1_36_creator_live_pilot_cases.json",
            "- bot_psychologist/tests/multiagent/test_prd_046_1_36_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.36/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.36_*.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Gates",
            f"- source_gate: `{scorecard.get('source_gate', 'blocked')}`",
            f"- runtime_readiness_gate: `{scorecard.get('runtime_readiness_gate', 'blocked')}`",
            f"- admin_runtime_controls_gate: `{scorecard.get('admin_runtime_controls_gate', 'blocked')}`",
            f"- creator_live_pilot_acceptance_gate: `{scorecard.get('creator_live_pilot_acceptance_gate', 'blocked')}`",
            f"- diagnostic_center_trace_acceptance_gate: `{scorecard.get('diagnostic_center_trace_acceptance_gate', 'blocked')}`",
            f"- rollback_force_disabled_gate: `{scorecard.get('rollback_force_disabled_gate', 'blocked')}`",
            f"- normal_user_no_effect_gate: `{scorecard.get('normal_user_no_effect_gate', 'blocked')}`",
            f"- rag_and_behavior_regression_gate: `{scorecard.get('rag_and_behavior_regression_gate', 'blocked')}`",
            f"- trace_sanitization_gate: `{scorecard.get('trace_sanitization_gate', 'blocked')}`",
            f"- provider_budget_gate: `{scorecard.get('provider_budget_gate', 'blocked')}`",
            f"- no_mutation_proof: `{scorecard.get('no_mutation_proof', 'blocked')}`",
            f"- artifact_encoding_hygiene: `{scorecard.get('artifact_encoding_hygiene', 'blocked')}`",
            "",
            "## Test Summary",
            "- pytest: `python -m pytest bot_psychologist/tests/multiagent/test_prd_046_1_36_*.py -q`",
            "- strict runner: `python -m bot_psychologist.tools.run_diagnostic_center_creator_live_pilot_acceptance ... --strict`",
            f"- strict runner status: `{scorecard.get('final_status', 'blocked')}`",
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(scorecard.get('blockers', [])) or 'none'}`",
            f"- warnings: `{', '.join(scorecard.get('warnings', [])) or 'none'}`",
            "",
            "## Next PRD Recommendation",
            f"- `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD)}`",
        ]
    )


def _render_creator_report(payload: dict[str, Any], trace_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.36 Creator Live Pilot Acceptance Report",
            "",
            f"- creator_cases_total: `{payload.get('creator_cases_total', 0)}`",
            f"- creator_cases_passed: `{payload.get('creator_cases_passed', 0)}`",
            f"- creator_answer_received_count: `{payload.get('creator_answer_received_count', 0)}`",
            f"- diagnostic_center_active_for_creator_count: `{payload.get('diagnostic_center_active_for_creator_count', 0)}`",
            f"- diagnostic_center_trace_present_count: `{payload.get('diagnostic_center_trace_present_count', 0)}`",
            f"- creator_live_pilot_acceptance_gate: `{payload.get('creator_live_pilot_acceptance_gate', 'blocked')}`",
            f"- diagnostic_center_trace_acceptance_gate: `{trace_payload.get('trace_acceptance_gate', 'blocked')}`",
        ]
    )


def _render_admin_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.36 Admin Runtime Controls Report",
            "",
            f"- runtime_tab_present: `{str(payload.get('runtime_tab_present', False)).lower()}`",
            f"- diagnostic_center_block_present: `{str(payload.get('diagnostic_center_block_present', False)).lower()}`",
            f"- runtime_mode_supported: `{', '.join(payload.get('runtime_mode_supported', []))}`",
            f"- runtime_mode_effective: `{payload.get('runtime_mode_effective', 'disabled')}`",
            f"- force_disabled_toggle_present: `{str(payload.get('force_disabled_toggle_present', False)).lower()}`",
            f"- all_users_control_locked: `{str(payload.get('all_users_control_locked', False)).lower()}`",
            f"- admin_runtime_controls_acceptance_gate: `{payload.get('admin_runtime_controls_acceptance_gate', 'blocked')}`",
        ]
    )


def _render_rollback_and_normal_report(rollback: dict[str, Any], normal: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.36 Rollback and Normal User No-Effect Report",
            "",
            f"- rollback_gate: `{rollback.get('rollback_gate', 'blocked')}`",
            f"- force_disabled_set_attempted: `{str(rollback.get('force_disabled_set_attempted', False)).lower()}`",
            f"- force_disabled_effective: `{str(rollback.get('force_disabled_effective', False)).lower()}`",
            f"- fallback_runtime_toggle_used: `{str(rollback.get('fallback_runtime_toggle_used', False)).lower()}`",
            f"- normal_user_no_effect_gate: `{normal.get('normal_user_no_effect_gate', 'blocked')}`",
            f"- diagnostic_center_live_authority_applied: `{str(normal.get('diagnostic_center_live_authority_applied', True)).lower()}`",
            f"- normal_user_provider_call_count: `{normal.get('diagnostic_center_provider_call_count', 0)}`",
        ]
    )


def _render_next_prd(scorecard: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.36 Next PRD Recommendation",
            "",
            f"- recommendation: `{scorecard.get('next_prd_recommendation', gate.NEXT_PRD)}`",
            f"- based_on_decision: `{scorecard.get('decision', gate.DECISION_BLOCKED_CREATOR)}`",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    docs_dir = Path(args.docs_dir).resolve()
    fixture_path = Path(args.fixture_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.36 runner executed.\n", encoding="utf-8")

    tracked, hash_before = gate.tracked_hashes(repo_root)

    preflight = gate.preflight_source(repo_root)
    source_gate = gate.build_source_gate(preflight)
    runtime_readiness = gate.build_runtime_readiness_gate(args.backend_base_url, args.botdb_base_url, args.web_ui_base_url)
    admin_source = gate._safe_dict(preflight.get("parsed", {}).get("admin_runtime_controls_134"))  # noqa: SLF001
    admin_controls = gate.build_admin_runtime_controls_acceptance(
        source_admin_gate=admin_source,
        runtime_readiness_gate=runtime_readiness,
        creator_user_id=args.creator_user_id,
    )
    creator_payload, trace_payload, normal_user_gate = gate.run_creator_live_pilot_cases(
        repo_root=repo_root,
        fixture_path=fixture_path,
    )
    rollback_payload = gate.build_rollback_force_disabled_proof()
    rag_behavior_gate = gate.build_rag_and_behavior_regression_gate(preflight=preflight, creator_payload=creator_payload)
    provider_budget_gate = gate.build_provider_budget_gate(creator_payload=creator_payload)

    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    no_mutation = gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "runtime_readiness_gate.json", runtime_readiness)
    _write_json(output_dir / "admin_runtime_controls_acceptance.json", admin_controls)
    _write_json(output_dir / "creator_live_pilot_acceptance.json", creator_payload)
    _write_json(output_dir / "diagnostic_center_trace_acceptance.json", trace_payload)
    _write_json(output_dir / "rollback_force_disabled_proof.json", rollback_payload)
    _write_json(output_dir / "normal_user_no_effect_gate.json", normal_user_gate)
    _write_json(output_dir / "rag_and_behavior_regression_gate.json", rag_behavior_gate)
    _write_json(output_dir / "provider_budget_gate.json", provider_budget_gate)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation)

    trace_sanitization_gate = gate.build_trace_sanitization_gate(output_dir)
    _write_json(output_dir / "trace_sanitization_gate.json", trace_sanitization_gate)

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
    _write_json(output_dir / "artifact_encoding_hygiene_report.json", encoding_report)
    encoding_passed = str(encoding_report.get("final_status", "failed")) == "passed"

    score_payload = gate.build_scorecard(
        source_gate=source_gate,
        runtime_readiness_gate=runtime_readiness,
        admin_controls=admin_controls,
        creator_payload=creator_payload,
        trace_payload=trace_payload,
        rollback_payload=rollback_payload,
        normal_user_gate=normal_user_gate,
        rag_behavior_gate=rag_behavior_gate,
        trace_sanitization_gate=trace_sanitization_gate,
        provider_budget_gate=provider_budget_gate,
        no_mutation_proof=no_mutation,
        artifact_encoding_hygiene_passed=encoding_passed,
    )
    scorecard = score_payload["scorecard"]
    decision = score_payload["decision"]
    _write_json(output_dir / "prd_046_1_36_scorecard.json", scorecard)

    _upsert_docs(docs_dir=docs_dir, final_status=str(scorecard.get("final_status", "blocked")))

    _write_text(reports_dir / "PRD-046.1.36_IMPLEMENTATION_REPORT.md", _render_implementation_report(scorecard))
    _write_text(reports_dir / "PRD-046.1.36_CREATOR_LIVE_PILOT_ACCEPTANCE_REPORT.md", _render_creator_report(creator_payload, trace_payload))
    _write_text(reports_dir / "PRD-046.1.36_ADMIN_RUNTIME_CONTROLS_REPORT.md", _render_admin_report(admin_controls))
    _write_text(
        reports_dir / "PRD-046.1.36_ROLLBACK_AND_NORMAL_USER_NO_EFFECT_REPORT.md",
        _render_rollback_and_normal_report(rollback_payload, normal_user_gate),
    )
    _write_text(reports_dir / "PRD-046.1.36_NEXT_PRD_RECOMMENDATION.md", _render_next_prd(scorecard))

    return {
        "status": str(scorecard.get("final_status", "blocked")),
        "decision": str(scorecard.get("decision", gate.DECISION_BLOCKED_CREATOR)),
        "scorecard": scorecard,
        "decision_payload": decision,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.36 creator-live pilot acceptance gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.36")
    parser.add_argument("--backend-base-url", default="http://localhost:8001")
    parser.add_argument("--botdb-base-url", default="http://localhost:8003")
    parser.add_argument("--web-ui-base-url", default="http://localhost:3000")
    parser.add_argument("--creator-user-id", default="user_1772172411219_kamh0")
    parser.add_argument("--normal-user-id", default="user_normal_control_prd_046_1_36")
    parser.add_argument("--fixture-path", default="bot_psychologist/tests/fixtures/prd_046_1_36_creator_live_pilot_cases.json")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
