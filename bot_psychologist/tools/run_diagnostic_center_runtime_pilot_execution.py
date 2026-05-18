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

from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from bot_agent.multiagent import diagnostic_center_runtime_pilot_execution as execution
from tools import validate_prd_artifact_encoding as encoding_validator

PRD = "PRD-046.1.20"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = eval_pack.runtime_hashes(repo_root)
    _ = tracked, runtime_tracked

    preflight = execution.preflight_source(source_dir, reports_dir)
    source_gate = execution.build_source_gate(preflight["parsed"], preflight["ok"])

    artifacts = execution.build_execution_artifacts(preflight["parsed"], repo_root, output_dir)
    artifacts["source_gate"] = source_gate

    no_mutation_proof = execution.build_no_mutation_proof(
        repo_root=repo_root,
        hash_before=hash_before,
        runtime_hash_before=runtime_hash_before,
    )
    docs_sync = execution.build_docs_sync_status(repo_root)

    hard_stop_evaluation = execution.build_hard_stop_evaluation(
        limited_live_smoke_results=artifacts["limited_live_smoke_results"],
        safety_gate=artifacts["safety_kb_boundary_gate"],
        trace_gate=artifacts["trace_sanitization_gate"],
        rollback_postcheck=artifacts["rollback_postcheck"],
        production_mutation_detected=bool(no_mutation_proof.get("production_mutation_detected", False)),
    )

    scorecard, decision_payload = execution.decide_final_status(
        source_gate=artifacts["source_gate"],
        preflight_gate=artifacts["preflight_gate"],
        execution_manifest=artifacts["execution_manifest"],
        limited_live_smoke_results=artifacts["limited_live_smoke_results"],
        quality_delta=artifacts["baseline_vs_pilot_quality_delta"],
        safety_gate=artifacts["safety_kb_boundary_gate"],
        trace_gate=artifacts["trace_sanitization_gate"],
        rollback_precheck=artifacts["rollback_precheck"],
        rollback_postcheck=artifacts["rollback_postcheck"],
        hard_stop=hard_stop_evaluation,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_synced=bool(docs_sync.get("docs_synced_before_execution", False)),
    )

    monitoring_scorecard = dict(scorecard)
    monitoring_scorecard["schema_version"] = "diagnostic_center_runtime_pilot_monitoring_scorecard_v1"
    monitoring_scorecard["prd"] = PRD

    _write_json(output_dir / "source_gate.json", artifacts["source_gate"])
    _write_json(output_dir / "preflight_gate.json", artifacts["preflight_gate"])
    _write_json(output_dir / "execution_manifest.json", artifacts["execution_manifest"])
    _write_json(output_dir / "toggle_state_before.json", artifacts["toggle_state_before"])
    _write_json(output_dir / "rollback_precheck.json", artifacts["rollback_precheck"])
    _write_json(output_dir / "pilot_operator_trace_samples_sanitized.json", artifacts["pilot_operator_trace_samples_sanitized"])
    _write_json(output_dir / "normal_user_control_trace_samples_sanitized.json", artifacts["normal_user_control_trace_samples_sanitized"])
    _write_json(output_dir / "limited_live_smoke_results.json", artifacts["limited_live_smoke_results"])
    _write_json(output_dir / "baseline_vs_pilot_quality_delta.json", artifacts["baseline_vs_pilot_quality_delta"])
    _write_json(output_dir / "safety_kb_boundary_gate.json", artifacts["safety_kb_boundary_gate"])
    _write_json(output_dir / "trace_sanitization_gate.json", artifacts["trace_sanitization_gate"])
    _write_json(output_dir / "rollback_postcheck.json", artifacts["rollback_postcheck"])
    _write_json(output_dir / "hard_stop_evaluation.json", hard_stop_evaluation)
    _write_json(output_dir / "monitoring_scorecard.json", monitoring_scorecard)
    _write_json(output_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = output_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.20 runner executed.\n", encoding="utf-8")

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
    scorecard, decision_payload = execution.decide_final_status(
        source_gate=artifacts["source_gate"],
        preflight_gate=artifacts["preflight_gate"],
        execution_manifest=artifacts["execution_manifest"],
        limited_live_smoke_results=artifacts["limited_live_smoke_results"],
        quality_delta=artifacts["baseline_vs_pilot_quality_delta"],
        safety_gate=artifacts["safety_kb_boundary_gate"],
        trace_gate=artifacts["trace_sanitization_gate"],
        rollback_precheck=artifacts["rollback_precheck"],
        rollback_postcheck=artifacts["rollback_postcheck"],
        hard_stop=hard_stop_evaluation,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_synced=bool(docs_sync.get("docs_synced_before_execution", False)),
    )
    monitoring_scorecard = dict(scorecard)
    monitoring_scorecard["schema_version"] = "diagnostic_center_runtime_pilot_monitoring_scorecard_v1"
    monitoring_scorecard["prd"] = PRD
    _write_json(output_dir / "monitoring_scorecard.json", monitoring_scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.20 Diagnostic Center controlled runtime pilot execution gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.19")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.20")
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
