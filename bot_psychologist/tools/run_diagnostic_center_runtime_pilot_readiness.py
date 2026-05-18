from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
DEFAULT_REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from bot_agent.multiagent import diagnostic_center_runtime_pilot_readiness as readiness
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.19"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = eval_pack.runtime_hashes(repo_root)

    preflight = readiness.preflight_source(source_dir, reports_dir)
    source_gate = readiness.build_source_gate(preflight["parsed"], preflight["ok"])
    pilot_scope = readiness.build_pilot_scope()
    cohort_policy = readiness.build_cohort_policy()
    toggle_matrix = readiness.build_toggle_matrix()
    runtime_preflight_requirements = readiness.build_runtime_preflight_requirements()
    limited_live_smoke_plan = readiness.build_limited_live_smoke_plan()
    rollback_first_runbook = readiness.build_rollback_first_runbook()
    hard_stop_criteria = readiness.build_hard_stop_criteria()
    monitoring_artifact_contract = readiness.build_monitoring_artifact_contract()
    normal_user_guard = readiness.build_normal_user_guard()
    kb_governance_guard = readiness.build_kb_governance_guard()
    trace_sanitization_guard = readiness.build_trace_sanitization_guard()

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_tracked.items()}
    no_mutation_proof = eval_pack.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )
    docs_sync = readiness.build_docs_sync_status(repo_root)

    scorecard, decision_payload = readiness.decide_final_status(
        source_gate=source_gate,
        pilot_scope=pilot_scope,
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        runtime_preflight_requirements=runtime_preflight_requirements,
        limited_live_smoke_plan=limited_live_smoke_plan,
        rollback_first_runbook=rollback_first_runbook,
        hard_stop_criteria=hard_stop_criteria,
        monitoring_artifact_contract=monitoring_artifact_contract,
        normal_user_guard=normal_user_guard,
        kb_governance_guard=kb_governance_guard,
        trace_sanitization_guard=trace_sanitization_guard,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )

    _write_json(output_dir / "source_gate.json", source_gate)
    _write_json(output_dir / "pilot_scope.json", pilot_scope)
    _write_json(output_dir / "cohort_policy.json", cohort_policy)
    _write_json(output_dir / "toggle_matrix.json", toggle_matrix)
    _write_json(output_dir / "runtime_preflight_requirements.json", runtime_preflight_requirements)
    _write_json(output_dir / "limited_live_smoke_plan.json", limited_live_smoke_plan)
    _write_json(output_dir / "rollback_first_runbook.json", rollback_first_runbook)
    _write_json(output_dir / "hard_stop_criteria.json", hard_stop_criteria)
    _write_json(output_dir / "monitoring_artifact_contract.json", monitoring_artifact_contract)
    _write_json(output_dir / "normal_user_guard.json", normal_user_guard)
    _write_json(output_dir / "kb_governance_guard.json", kb_governance_guard)
    _write_json(output_dir / "trace_sanitization_guard.json", trace_sanitization_guard)
    _write_json(output_dir / "runtime_pilot_readiness_scorecard.json", scorecard)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.19 runner executed.\n", encoding="utf-8")

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

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    scorecard, decision_payload = readiness.decide_final_status(
        source_gate=source_gate,
        pilot_scope=pilot_scope,
        cohort_policy=cohort_policy,
        toggle_matrix=toggle_matrix,
        runtime_preflight_requirements=runtime_preflight_requirements,
        limited_live_smoke_plan=limited_live_smoke_plan,
        rollback_first_runbook=rollback_first_runbook,
        hard_stop_criteria=hard_stop_criteria,
        monitoring_artifact_contract=monitoring_artifact_contract,
        normal_user_guard=normal_user_guard,
        kb_governance_guard=kb_governance_guard,
        trace_sanitization_guard=trace_sanitization_guard,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    _write_json(output_dir / "runtime_pilot_readiness_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.19 Diagnostic Center runtime pilot readiness planning gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.18")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.19")
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) in {"passed", "passed_with_quality_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
