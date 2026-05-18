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

from bot_agent.multiagent import diagnostic_center_response_quality_calibration as calibration
from bot_agent.multiagent import diagnostic_center_response_quality_eval as eval_pack
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.18"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_logs_dir = Path(args.source_logs_dir).resolve()
    source_reports_dir = Path(args.source_reports_dir).resolve()
    scenarios_path = Path(args.scenarios).resolve()
    rubric_path = Path(args.rubric).resolve()
    response_candidates_path = Path(args.response_candidates).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = eval_pack.runtime_hashes(repo_root)

    preflight = calibration.preflight_source(source_logs_dir, source_reports_dir)
    source_gate = calibration.build_source_gate(preflight["parsed"], preflight["ok"])

    scenarios = calibration.load_scenarios(scenarios_path) if scenarios_path.exists() else []
    rubric_dimensions = calibration.load_rubric(rubric_path) if rubric_path.exists() else []
    candidates_by_scenario = calibration.load_candidates(response_candidates_path) if response_candidates_path.exists() else {}

    expanded_scenario_catalog = calibration.validate_expanded_scenario_catalog(scenarios)
    calibrated_rubric_validation = calibration.validate_calibrated_rubric(rubric_dimensions)
    expanded_candidate_catalog = calibration.build_expanded_candidate_catalog(candidates_by_scenario)

    source_weak_queue = dict(preflight["parsed"].get("source_weak_queue", {}))
    source_dimension_scorecard = dict(preflight["parsed"].get("source_dimension_scorecard", {}))
    weak_case_inventory = calibration.build_weak_case_inventory(
        source_weak_queue=source_weak_queue,
        source_dimension_scorecard=source_dimension_scorecard,
        scenarios=scenarios,
    )
    calibration_plan = calibration.build_calibration_plan(weak_case_inventory)

    if source_gate.get("source_gate_passed", False):
        (
            calibrated_eval_results,
            calibrated_dimension_scorecard,
            weak_case_closure_report,
            _metrics,
            _profile_totals,
            calibrated_weak_queue,
        ) = calibration.evaluate_calibrated(
            scenarios=scenarios,
            rubric_dimensions=rubric_dimensions,
            candidates_by_scenario=candidates_by_scenario,
        )
    else:
        calibrated_eval_results = {
            "schema_version": "calibrated_response_quality_eval_results_v1",
            "prd": PRD,
            "results": [],
            "metrics": {
                "acceptable_candidate_pass_rate": 0.0,
                "weak_candidate_detection_rate": 0.0,
                "hard_fail_detection_rate": 0.0,
                "state_depth_fit_weak_detection_rate": 0.0,
                "non_directiveness_weak_detection_rate": 0.0,
                "non_bookishness_weak_detection_rate": 0.0,
                "kb_boundary_respect_hard_fail_detection_rate": 0.0,
            },
            "profile_totals": {},
            "profile_detected": {},
        }
        calibrated_dimension_scorecard = {
            "schema_version": "calibrated_dimension_scorecard_v1",
            "prd": PRD,
            "dimensions": {},
            "lowest_scoring_dimensions": [],
            "hard_fail_counts": {},
            "state_depth_fit_weak_detection_rate": 0.0,
            "non_directiveness_weak_detection_rate": 0.0,
            "non_bookishness_weak_detection_rate": 0.0,
            "kb_boundary_respect_hard_fail_detection_rate": 0.0,
            "acceptable_candidate_pass_rate": 0.0,
            "weak_candidate_detection_rate": 0.0,
            "hard_fail_detection_rate": 0.0,
        }
        weak_case_closure_report = {
            "schema_version": "weak_case_closure_report_v1",
            "prd": PRD,
            "closure_groups": {},
            "remaining_known_limitations": ["source_gate_failed"],
            "blockers": ["source_gate_failed"],
            "ready": False,
        }
        calibrated_weak_queue = []

    kb_boundary_calibration_report = calibration.build_kb_boundary_calibration_report(
        list(calibrated_eval_results.get("results", []))
    )
    no_runtime_authority_gate = calibration.build_no_runtime_authority_expansion_gate(source_gate)

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_tracked.items()}
    no_mutation_proof = eval_pack.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    docs_sync = calibration.build_docs_sync_status(repo_root)
    scorecard, decision_payload = calibration.decide_final_status(
        source_gate=source_gate,
        weak_case_inventory=weak_case_inventory,
        calibration_plan=calibration_plan,
        expanded_scenario_catalog=expanded_scenario_catalog,
        expanded_candidate_catalog=expanded_candidate_catalog,
        calibrated_rubric_validation=calibrated_rubric_validation,
        calibrated_dimension_scorecard=calibrated_dimension_scorecard,
        kb_boundary_calibration_report=kb_boundary_calibration_report,
        no_runtime_authority_gate=no_runtime_authority_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )

    _write_json(out_dir / "source_gate.json", source_gate)
    _write_json(out_dir / "weak_case_inventory.json", weak_case_inventory)
    _write_json(out_dir / "calibration_plan.json", calibration_plan)
    _write_json(out_dir / "expanded_scenario_catalog.json", expanded_scenario_catalog)
    _write_json(out_dir / "expanded_candidate_catalog.json", expanded_candidate_catalog)
    _write_json(out_dir / "calibrated_rubric_validation.json", calibrated_rubric_validation)
    _write_json(out_dir / "calibrated_response_quality_eval_results.json", calibrated_eval_results)
    _write_json(out_dir / "calibrated_dimension_scorecard.json", calibrated_dimension_scorecard)
    _write_json(out_dir / "weak_case_closure_report.json", weak_case_closure_report)
    _write_json(out_dir / "kb_boundary_calibration_report.json", kb_boundary_calibration_report)
    _write_json(out_dir / "no_runtime_authority_expansion_gate.json", no_runtime_authority_gate)
    _write_json(out_dir / "diagnostic_center_response_quality_calibration_scorecard.json", scorecard)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.18 runner executed.\n", encoding="utf-8")

    encoding_report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD,
            logs_dir=str(out_dir),
            reports_dir=str(source_reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD,
            repo_root=str(repo_root),
            fixed_file=[],
        )
    )

    artifact_hygiene_passed = str(encoding_report.get("final_status", "failed")) == "passed"
    scorecard, decision_payload = calibration.decide_final_status(
        source_gate=source_gate,
        weak_case_inventory=weak_case_inventory,
        calibration_plan=calibration_plan,
        expanded_scenario_catalog=expanded_scenario_catalog,
        expanded_candidate_catalog=expanded_candidate_catalog,
        calibrated_rubric_validation=calibrated_rubric_validation,
        calibrated_dimension_scorecard=calibrated_dimension_scorecard,
        kb_boundary_calibration_report=kb_boundary_calibration_report,
        no_runtime_authority_gate=no_runtime_authority_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    _write_json(out_dir / "diagnostic_center_response_quality_calibration_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
        "weak_queue_count": len(calibrated_weak_queue),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.18 Diagnostic Center response quality calibration.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-logs-dir", default="TO_DO_LIST/logs/PRD-046.1.17")
    parser.add_argument("--source-reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--scenarios", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json")
    parser.add_argument("--rubric", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json")
    parser.add_argument("--response-candidates", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.18")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("status", "failed")) in {"passed", "passed_with_quality_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
