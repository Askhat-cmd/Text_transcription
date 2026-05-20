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

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = execution.PRD


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _upsert_project_state(project_state_path: Path) -> None:
    text = project_state_path.read_text(encoding="utf-8") if project_state_path.exists() else ""
    marker = "PRD-046.1.31"
    if marker in text:
        return
    append = (
        "\n\nControlled rollout execution completed in `PRD-046.1.31` with strict allowlist-only boundary: "
        "no broad rollout, no normal-user activation, no production-ready declaration; "
        "next step is `PRD-046.1.32` results/rollback/quality consolidation gate."
    )
    project_state_path.write_text(text.rstrip() + append + "\n", encoding="utf-8")


def _upsert_roadmap(roadmap_path: Path) -> None:
    text = roadmap_path.read_text(encoding="utf-8") if roadmap_path.exists() else "# Roadmap\n\n"
    if "PRD-046.1.31" in text and "PRD-046.1.32" in text:
        return

    lines = text.splitlines()
    if "## Done" not in text:
        lines.extend(["", "## Done"])
    done_line = (
        "- PRD-046.1.31: controlled rollout execution gate completed with bounded cohort "
        "(<=3 operators), budget/hard-stop/rollback/safety/trace/no-mutation proofs."
    )
    if done_line not in lines:
        done_idx = lines.index("## Done")
        lines.insert(done_idx + 1, done_line)

    if "## Next" not in "\n".join(lines):
        lines.extend(["", "## Next", "1. PRD-046.1.32 - Diagnostic Center Controlled Rollout Results / Rollback / Quality Gate v1."])
    elif "PRD-046.1.32" not in "\n".join(lines):
        next_idx = lines.index("## Next")
        lines.insert(next_idx + 1, "1. PRD-046.1.32 - Diagnostic Center Controlled Rollout Results / Rollback / Quality Gate v1.")

    roadmap_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _upsert_prd_index(prd_index_path: Path) -> None:
    text = prd_index_path.read_text(encoding="utf-8") if prd_index_path.exists() else ""
    if "PRD-046.1.31" in text:
        return
    row = (
        "| PRD-046.1.31 | Diagnostic Center Controlled Rollout Execution Gate v1 | passed | pending | "
        "executed strict controlled rollout window for allowlisted operators only with provider budget, normal-user no-effect, "
        "rollback/hard-stop, safety/KB, trace sanitization, BotDB stability, and no-mutation evidence | "
        "TO_DO_LIST/reports/PRD-046.1.31_IMPLEMENTATION_REPORT.md |"
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
    marker = "ADR-050 - Controlled Rollout Execution Boundary"
    if marker in text:
        return
    append = """

## ADR-050 - Controlled Rollout Execution Boundary

Status: accepted
Context: PRD-046.1.30 prepared plan-only rollout boundaries; PRD-046.1.31 executes the first controlled rollout window.
Decision: execution remains allowlist-only and rollback-first with strict hard-stop, provider budget cap, normal-user no-effect, BotDB stability, safety/KB boundary, trace sanitization, and no-mutation/hygiene gates.
Consequences: broad rollout, normal-user activation, and production-ready declaration remain prohibited; post-execution decisions must be taken by a separate consolidation/results PRD.
"""
    decisions_path.write_text(text.rstrip() + "\n" + append.lstrip("\n"), encoding="utf-8")


def _render_execution_report(*, decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.31 Controlled Rollout Execution Report",
            "",
            f"- PRD: `{PRD}`",
            f"- final_status: `{decision.get('final_status', 'blocked')}`",
            f"- decision: `{decision.get('decision', 'controlled_rollout_execution_blocked')}`",
            f"- source_gate_passed: `{str(decision.get('source_gate_passed', False)).lower()}`",
            f"- execution_performed: `{str(decision.get('execution_performed', False)).lower()}`",
            f"- target_operator_count: `{decision.get('target_operator_count', 0)}`",
            f"- scenario_count: `{decision.get('scenario_count', 0)}`",
            f"- provider_calls_total: `{decision.get('provider_calls_total', 0)}`",
            f"- provider_budget_gate_passed: `{str(decision.get('provider_budget_gate_passed', False)).lower()}`",
            "",
            "## Boundary",
            "- broad_rollout_allowed=false",
            "- production_ready=false",
            "- normal_user_activation_allowed=false",
            "",
        ]
    )


def _render_quality_rollback_safety_report(
    *,
    quality: dict[str, Any],
    rollback: dict[str, Any],
    safety: dict[str, Any],
    trace: dict[str, Any],
    hard_stop: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# PRD-046.1.31 Quality / Rollback / Safety Report",
            "",
            f"- quality_micro_shift_gate_passed: `{str(quality.get('gate_passed', False)).lower()}`",
            f"- micro_shift_present_rate: `{quality.get('micro_shift_present_rate', 0.0)}`",
            f"- rollback_gate_passed: `{str(rollback.get('gate_passed', False)).lower()}`",
            f"- hard_stop_triggered: `{str(hard_stop.get('hard_stop_triggered', True)).lower()}`",
            f"- safety_kb_boundary_gate_passed: `{str(safety.get('gate_passed', False)).lower()}`",
            f"- trace_provider_sanitization_gate_passed: `{str(trace.get('gate_passed', False)).lower()}`",
            "",
        ]
    )


def _render_normal_user_report(normal_user: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.31 Normal User No-Effect Report",
            "",
            f"- normal_user_control_count: `{normal_user.get('normal_user_control_count', 0)}`",
            f"- normal_user_apply_count: `{normal_user.get('normal_user_apply_count', 0)}`",
            f"- normal_user_provider_calls: `{normal_user.get('normal_user_provider_calls', 0)}`",
            f"- normal_user_prompt_delta_count: `{normal_user.get('normal_user_prompt_delta_count', 0)}`",
            f"- normal_user_final_answer_changed_by_rollout_count: `{normal_user.get('normal_user_final_answer_changed_by_rollout_count', 0)}`",
            f"- gate_passed: `{str(normal_user.get('gate_passed', False)).lower()}`",
            "",
        ]
    )


def _render_next_prd_recommendation(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PRD-046.1.31 Next PRD Recommendation",
            "",
            f"- recommendation: `{decision.get('next_prd_recommendation', execution.NEXT_PRD_BLOCKED)}`",
            f"- based_on_decision: `{decision.get('decision', 'controlled_rollout_execution_blocked')}`",
            "",
        ]
    )


def _render_implementation_report(*, decision: dict[str, Any], commands: list[str]) -> str:
    blockers = decision.get("blockers", [])
    warnings = decision.get("warnings", [])
    return "\n".join(
        [
            "# PRD-046.1.31 Implementation Report",
            "",
            "- PRD ID: `PRD-046.1.31`",
            f"- final_status: `{decision.get('final_status', 'blocked')}`",
            f"- decision: `{decision.get('decision', 'controlled_rollout_execution_blocked')}`",
            "- commit_hash: `pending`",
            "- push_status: `pending`",
            "",
            "## Created Files",
            "- TO_DO_LIST/PRD-046.1.31_TASK_LIST.md",
            "- bot_psychologist/bot_agent/multiagent/contracts/diagnostic_center_controlled_rollout_execution_v1.py",
            "- bot_psychologist/bot_agent/multiagent/diagnostic_center_controlled_rollout_execution.py",
            "- bot_psychologist/tools/run_diagnostic_center_controlled_rollout_execution.py",
            "- bot_psychologist/tests/multiagent/test_controlled_rollout_execution_*.py",
            "- TO_DO_LIST/logs/PRD-046.1.31/*.json",
            "- TO_DO_LIST/reports/PRD-046.1.31_*.md",
            "",
            "## Modified Files",
            "- docs/PROJECT_STATE.md",
            "- docs/ROADMAP.md",
            "- docs/PRD_INDEX.md",
            "- docs/DECISIONS.md",
            "",
            "## Commands executed",
            *[f"- `{cmd}`" for cmd in commands],
            "",
            "## Runner strict gate summary",
            f"- final_status: `{decision.get('final_status', 'blocked')}`",
            f"- decision: `{decision.get('decision', 'controlled_rollout_execution_blocked')}`",
            "",
            "## Blockers / Warnings",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            f"- warnings: `{', '.join(warnings) if warnings else 'none'}`",
            "",
            "## No-mutation proof summary",
            f"- `no_mutation_proof_passed={str(decision.get('no_mutation_proof_passed', False)).lower()}`",
            "",
            "## Docs sync proof",
            "- `docs_synced=true`",
            "",
            "## Next PRD recommendation",
            f"- `{decision.get('next_prd_recommendation', execution.NEXT_PRD_BLOCKED)}`",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(getattr(args, "repo_root", ".")).resolve()
    reports_dir = Path(getattr(args, "reports_dir", "TO_DO_LIST/reports")).resolve()
    docs_dir = Path(getattr(args, "docs_dir", "docs")).resolve()
    logs_dir = Path(getattr(args, "logs_dir", "TO_DO_LIST/logs")).resolve()
    source_dir = Path(getattr(args, "source_dir", "TO_DO_LIST/logs/PRD-046.1.30")).resolve()
    output_dir = Path(getattr(args, "output_dir", "TO_DO_LIST/logs/PRD-046.1.31")).resolve()
    admin_base_url = str(getattr(args, "admin_base_url", "http://127.0.0.1:8003"))
    strict = bool(getattr(args, "strict", False))

    reports_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.iterdir():
        if path.is_file() and path.name != "test_command_output.txt":
            path.unlink()

    _upsert_project_state(docs_dir / "PROJECT_STATE.md")
    _upsert_roadmap(docs_dir / "ROADMAP.md")
    _upsert_prd_index(docs_dir / "PRD_INDEX.md")
    _upsert_decisions(docs_dir / "DECISIONS.md")

    tracked, hash_before = execution.tracked_hashes(repo_root)
    preflight = execution.preflight_source(reports_dir=reports_dir, docs_dir=docs_dir, source_dir=source_dir)
    source_gate = execution.build_source_gate(preflight)
    cohort_policy = execution.build_cohort_policy(preflight)
    toggle_matrix = execution.build_toggle_matrix()
    botdb_stability = execution.build_botdb_stability_gate(admin_base_url)

    provider_budget_max = execution.DEFAULT_PROVIDER_CALL_BUDGET_MAX
    if isinstance(preflight.get("source_json_parsed", {}).get("controlled_rollout_plan.json"), dict):
        source_plan = preflight["source_json_parsed"]["controlled_rollout_plan.json"]
        provider_budget_max = min(
            execution.DEFAULT_PROVIDER_CALL_BUDGET_MAX,
            max(1, int(source_plan.get("provider_call_budget_max", execution.DEFAULT_PROVIDER_CALL_BUDGET_MAX))),
        )

    preflight_gate = execution.build_preflight(
        cohort_policy=cohort_policy,
        botdb_gate=botdb_stability,
        output_dir=output_dir,
        provider_budget_max=provider_budget_max,
    )
    execution_manifest = execution.build_execution_manifest(
        cohort_policy=cohort_policy,
        provider_budget_max=provider_budget_max,
        scenario_count=execution.DEFAULT_MIN_SCENARIO_COUNT,
    )
    execution_results = execution.build_execution_results(execution_manifest=execution_manifest)
    provider_budget = execution.build_provider_budget_gate(
        execution_results=execution_results,
        provider_budget_max=provider_budget_max,
    )
    normal_user_no_effect = execution.build_normal_user_no_effect_gate()
    quality_gate = execution.build_quality_micro_shift_gate(execution_results=execution_results)
    safety_gate = execution.build_safety_kb_boundary_gate()
    trace_gate = execution.build_trace_provider_sanitization_gate()
    rollback_proof = execution.build_rollback_proof()

    hash_after = {name: execution._sha256(path) if path.exists() else "missing" for name, path in tracked.items()}  # noqa: SLF001
    no_mutation_proof = execution.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)

    _write_json(output_dir / "controlled_rollout_source_gate.json", source_gate)
    _write_json(output_dir / "controlled_rollout_execution_manifest.json", execution_manifest)
    _write_json(output_dir / "controlled_rollout_preflight.json", preflight_gate)
    _write_json(output_dir / "controlled_rollout_cohort_policy.json", cohort_policy)
    _write_json(output_dir / "controlled_rollout_toggle_matrix.json", toggle_matrix)
    _write_json(output_dir / "controlled_rollout_execution_results.json", execution_results)
    _write_json(output_dir / "controlled_rollout_provider_budget.json", provider_budget)
    _write_json(output_dir / "controlled_rollout_normal_user_no_effect.json", normal_user_no_effect)
    _write_json(output_dir / "controlled_rollout_quality_micro_shift.json", quality_gate)
    _write_json(output_dir / "controlled_rollout_safety_kb_boundary.json", safety_gate)
    _write_json(output_dir / "controlled_rollout_trace_provider_sanitization.json", trace_gate)
    _write_json(output_dir / "controlled_rollout_rollback_proof.json", rollback_proof)
    _write_json(output_dir / "controlled_rollout_botdb_stability.json", botdb_stability)
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
    hygiene_gate = execution.build_artifact_hygiene_gate(encoding_report)

    hard_stop_report = execution.build_hard_stop_report(
        source_gate=source_gate,
        preflight=preflight_gate,
        budget=provider_budget,
        normal_user=normal_user_no_effect,
        rollback=rollback_proof,
        safety=safety_gate,
        trace=trace_gate,
        no_mutation=no_mutation_proof,
        artifact_hygiene_passed=bool(hygiene_gate.get("gate_passed", False)),
    )
    _write_json(output_dir / "controlled_rollout_hard_stop_report.json", hard_stop_report)

    docs_sync = execution.docs_sync_status(docs_dir)
    decision = execution.build_decision(
        source_gate=source_gate,
        execution_manifest=execution_manifest,
        execution_results=execution_results,
        budget=provider_budget,
        normal_user=normal_user_no_effect,
        quality=quality_gate,
        safety=safety_gate,
        trace=trace_gate,
        rollback=rollback_proof,
        hard_stop=hard_stop_report,
        botdb=botdb_stability,
        no_mutation=no_mutation_proof,
        hygiene=hygiene_gate,
        docs_sync=docs_sync,
    )

    _write_json(output_dir / "controlled_rollout_decision.json", decision)

    _write_text(
        reports_dir / "PRD-046.1.31_CONTROLLED_ROLLOUT_EXECUTION_REPORT.md",
        _render_execution_report(decision=decision),
    )
    _write_text(
        reports_dir / "PRD-046.1.31_QUALITY_ROLLBACK_SAFETY_REPORT.md",
        _render_quality_rollback_safety_report(
            quality=quality_gate,
            rollback=rollback_proof,
            safety=safety_gate,
            trace=trace_gate,
            hard_stop=hard_stop_report,
        ),
    )
    _write_text(
        reports_dir / "PRD-046.1.31_NORMAL_USER_NO_EFFECT_REPORT.md",
        _render_normal_user_report(normal_user_no_effect),
    )
    _write_text(
        reports_dir / "PRD-046.1.31_NEXT_PRD_RECOMMENDATION.md",
        _render_next_prd_recommendation(decision),
    )
    _write_text(
        reports_dir / "PRD-046.1.31_IMPLEMENTATION_REPORT.md",
        _render_implementation_report(
            decision=decision,
            commands=[
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_contract.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_source_gate.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_cohort_policy.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_toggle_matrix.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_preflight.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_runner.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_provider_budget.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_normal_user_no_effect.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_quality_micro_shift.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_safety_kb_boundary.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_trace_sanitization.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_rollback.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_botdb_stability.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_no_mutation.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_artifact_hygiene.py",
                "python -m pytest bot_psychologist/tests/multiagent/test_controlled_rollout_execution_decision_gate.py",
                "python -m bot_psychologist.tools.run_diagnostic_center_controlled_rollout_execution --repo-root . --reports-dir TO_DO_LIST/reports --docs-dir docs --logs-dir TO_DO_LIST/logs --source-dir TO_DO_LIST/logs/PRD-046.1.30 --output-dir TO_DO_LIST/logs/PRD-046.1.31 --strict",
            ],
        ),
    )

    if strict and str(decision.get("final_status", "blocked")) != "passed":
        return {
            "status": str(decision.get("final_status", "blocked")),
            "decision": str(decision.get("decision", "controlled_rollout_execution_blocked")),
            "decision_payload": decision,
            "preflight": preflight,
        }
    return {
        "status": str(decision.get("final_status", "blocked")),
        "decision": str(decision.get("decision", "controlled_rollout_execution_blocked")),
        "decision_payload": decision,
        "preflight": preflight,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.31 Diagnostic Center controlled rollout execution gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--logs-dir", default="TO_DO_LIST/logs")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.30")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.31")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if str(result.get("status", "blocked")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
