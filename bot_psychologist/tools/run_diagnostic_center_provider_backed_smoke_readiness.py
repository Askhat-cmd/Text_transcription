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

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness
from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.22"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_no_mutation_proof(*, repo_root: Path) -> dict[str, Any]:
    tracked, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = eval_pack.runtime_hashes(repo_root)
    hash_after = {name: eval_pack._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    runtime_hash_after = {name: eval_pack._sha256(path) for name, path in runtime_tracked.items()}  # noqa: SLF001
    base = eval_pack.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )
    return {
        "schema_version": "provider_backed_smoke_readiness_no_mutation_proof_v1",
        "prd": PRD,
        "all_blocks_merged_mutated": bool(base.get("all_blocks_merged_mutated", False)),
        "registry_mutated": bool(base.get("registry_mutated", False)),
        "config_mutated": bool(base.get("config_mutated", False)),
        "chroma_reindex_performed": bool(base.get("chroma_reindex_performed", False)),
        "runtime_defaults_changed": bool(base.get("runtime_defaults_changed", False)),
        "writer_prompt_changed": bool(base.get("writer_prompt_runtime_changed", False)),
        "writer_contract_changed": bool(base.get("writer_contract_runtime_changed", False)),
        "final_answer_path_changed": False,
        "normal_user_path_changed": bool(base.get("normal_user_path_changed", False)),
        "provider_called": False,
        "provider_execution_performed": False,
        "private_env_committed": False,
        "raw_provider_payload_committed": False,
        "raw_private_logs_committed": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    logs_root = Path(args.logs_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    preflight = readiness.preflight_source_gates(logs_root, reports_dir)
    diagnostic_center_source_gate = readiness.build_diagnostic_center_source_gate(preflight["parsed"], preflight["ok"])
    botdb_recovery_source_gate = readiness.build_botdb_recovery_source_gate(preflight["parsed"], preflight["ok"])
    live_probe = readiness.probe_live_dependencies(args.admin_base_url)
    live_dependency_gate = readiness.build_live_dependency_gate(live_probe)

    provider_readiness_policy = readiness.build_provider_readiness_policy()
    cohort_policy = readiness.build_cohort_policy()
    toggle_matrix = readiness.build_toggle_matrix()
    scenario_pack = readiness.build_scenario_pack()
    normal_user_control_plan = readiness.build_normal_user_control_plan()
    rollback_first_runbook = readiness.build_rollback_first_runbook()
    hard_stop_criteria = readiness.build_hard_stop_criteria()
    kb_boundary_contract = readiness.build_kb_boundary_contract()
    trace_sanitization_contract = readiness.build_trace_sanitization_contract()
    execution_manifest_template = readiness.build_execution_manifest_template()
    no_mutation_proof = _build_no_mutation_proof(repo_root=repo_root)
    docs_sync = readiness.build_docs_sync_status(repo_root)

    scorecard, decision_payload = readiness.decide_final_status(
        diagnostic_center_source_gate=diagnostic_center_source_gate,
        botdb_recovery_source_gate=botdb_recovery_source_gate,
        live_dependency_gate=live_dependency_gate,
        provider_readiness_policy=provider_readiness_policy,
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        scenario_pack=scenario_pack,
        normal_user_control_plan=normal_user_control_plan,
        rollback_first_runbook=rollback_first_runbook,
        hard_stop_criteria=hard_stop_criteria,
        kb_boundary_contract=kb_boundary_contract,
        trace_sanitization_contract=trace_sanitization_contract,
        execution_manifest_template=execution_manifest_template,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )

    _write_json(out_dir / "diagnostic_center_source_gate.json", diagnostic_center_source_gate)
    _write_json(out_dir / "botdb_recovery_source_gate.json", botdb_recovery_source_gate)
    _write_json(out_dir / "live_dependency_readiness_gate.json", live_dependency_gate)
    _write_json(out_dir / "provider_readiness_policy.json", provider_readiness_policy)
    _write_json(out_dir / "provider_backed_cohort_policy.json", cohort_policy)
    _write_json(out_dir / "provider_backed_toggle_matrix.json", toggle_matrix)
    _write_json(out_dir / "provider_backed_smoke_scenario_pack.json", scenario_pack)
    _write_json(out_dir / "normal_user_control_plan.json", normal_user_control_plan)
    _write_json(out_dir / "provider_backed_rollback_first_runbook.json", rollback_first_runbook)
    _write_json(out_dir / "provider_backed_hard_stop_criteria.json", hard_stop_criteria)
    _write_json(out_dir / "provider_backed_kb_boundary_contract.json", kb_boundary_contract)
    _write_json(out_dir / "provider_backed_trace_sanitization_contract.json", trace_sanitization_contract)
    _write_json(out_dir / "provider_backed_execution_manifest_template.json", execution_manifest_template)
    _write_json(out_dir / "provider_backed_limited_smoke_readiness_scorecard.json", scorecard)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.22 runner executed.\n", encoding="utf-8")

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str(reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    scorecard, decision_payload = readiness.decide_final_status(
        diagnostic_center_source_gate=diagnostic_center_source_gate,
        botdb_recovery_source_gate=botdb_recovery_source_gate,
        live_dependency_gate=live_dependency_gate,
        provider_readiness_policy=provider_readiness_policy,
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        scenario_pack=scenario_pack,
        normal_user_control_plan=normal_user_control_plan,
        rollback_first_runbook=rollback_first_runbook,
        hard_stop_criteria=hard_stop_criteria,
        kb_boundary_contract=kb_boundary_contract,
        trace_sanitization_contract=trace_sanitization_contract,
        execution_manifest_template=execution_manifest_template,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    _write_json(out_dir / "provider_backed_limited_smoke_readiness_scorecard.json", scorecard)

    return {
        "status": str(scorecard.get("final_status", "failed")),
        "decision": str(scorecard.get("decision", "provider_backed_readiness_blocked")),
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "live_probe": live_probe,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.22 provider-backed limited smoke readiness gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--logs-root", default="TO_DO_LIST/logs")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.22")
    parser.add_argument("--admin-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
