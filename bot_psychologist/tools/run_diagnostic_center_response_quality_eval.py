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
from tools import validate_prd_artifact_encoding as encoding_validator


PRD = "PRD-046.1.17"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    source_dir = Path(args.source_dir).resolve()
    scenarios_path = Path(args.scenarios).resolve()
    rubric_path = Path(args.rubric).resolve()
    response_candidates_path = Path(args.response_candidates).resolve()
    out_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    tracked, hash_before = eval_pack.tracked_hashes(repo_root)
    runtime_tracked, runtime_hash_before = eval_pack.runtime_hashes(repo_root)
    preflight = eval_pack.preflight_source(source_dir, repo_root)
    source_gate = eval_pack.build_source_gate(preflight["parsed"], preflight["ok"])

    if scenarios_path.exists():
        scenarios = eval_pack.load_scenarios(scenarios_path)
    else:
        scenarios = []
    if rubric_path.exists():
        rubric_dimensions = eval_pack.load_rubric(rubric_path)
    else:
        rubric_dimensions = []
    if response_candidates_path.exists():
        candidates_by_scenario = eval_pack.load_candidates(response_candidates_path)
    else:
        candidates_by_scenario = {}

    scenario_catalog = eval_pack.validate_scenarios(scenarios)
    rubric_validation = eval_pack.validate_rubric(rubric_dimensions)

    if source_gate.get("source_gate_passed", False):
        results, weak_queue, eval_metrics = eval_pack.evaluate_response_quality(
            scenarios=scenarios,
            rubric_dimensions=rubric_dimensions,
            candidates_by_scenario=candidates_by_scenario,
        )
    else:
        results = []
        weak_queue = []
        eval_metrics = {
            "dimension_report": {
                "schema_version": "response_quality_dimension_scorecard_v1",
                "prd": PRD,
                "dimensions": {},
                "lowest_scoring_dimensions": [],
                "hard_fail_counts": {},
                "weak_candidate_detection_rate": 0.0,
                "acceptable_candidate_pass_rate": 0.0,
                "hard_fail_detection_rate": 0.0,
                "recommendations_for_next_prd": ["fix_source_gate_first"],
            },
            "metrics": {
                "acceptable_candidate_pass_rate": 0.0,
                "weak_candidate_detection_rate": 0.0,
                "hard_fail_detection_rate": 0.0,
                "hard_fail_counts": {},
            },
        }

    kb_boundary_eval = eval_pack.build_kb_internal_lens_boundary_eval(results)
    no_runtime_authority_gate = eval_pack.build_no_runtime_authority_expansion_gate(source_gate)

    hash_after = {name: _sha256(path) for name, path in tracked.items()}
    runtime_hash_after = {name: _sha256(path) for name, path in runtime_tracked.items()}
    no_mutation_proof = eval_pack.build_no_mutation_proof(
        hash_before=hash_before,
        hash_after=hash_after,
        runtime_hash_before=runtime_hash_before,
        runtime_hash_after=runtime_hash_after,
    )

    docs_sync = eval_pack.build_docs_sync_status(repo_root)
    scorecard, decision_payload = eval_pack.decide_final_status(
        source_gate=source_gate,
        scenario_catalog=scenario_catalog,
        rubric_validation=rubric_validation,
        metrics=eval_metrics["metrics"],
        kb_boundary_eval=kb_boundary_eval,
        no_runtime_authority_gate=no_runtime_authority_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=True,
        docs_sync=docs_sync,
    )

    eval_results_payload = {
        "schema_version": "response_quality_eval_results_v1",
        "prd": PRD,
        "results": results,
        "metrics": eval_metrics["metrics"],
        "final_status": scorecard["final_status"],
        "decision": scorecard["decision"],
    }

    _write_json(out_dir / "source_gate.json", source_gate)
    _write_json(out_dir / "response_quality_scenario_catalog.json", scenario_catalog)
    _write_json(out_dir / "response_quality_rubric_validation.json", rubric_validation)
    _write_json(out_dir / "response_quality_eval_results.json", eval_results_payload)
    _write_json(out_dir / "response_quality_dimension_scorecard.json", eval_metrics["dimension_report"])
    _write_json(out_dir / "response_quality_weak_case_queue.json", {"schema_version": "response_quality_weak_case_queue_v1", "prd": PRD, "items": weak_queue})
    _write_json(out_dir / "kb_internal_lens_response_boundary_eval.json", kb_boundary_eval)
    _write_json(out_dir / "no_runtime_authority_expansion_gate.json", no_runtime_authority_gate)
    _write_json(out_dir / "diagnostic_center_response_quality_eval_scorecard.json", scorecard)
    _write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)

    test_log = out_dir / "test_command_output.txt"
    if not test_log.exists():
        test_log.write_text("PRD-046.1.17 runner executed.\n", encoding="utf-8")

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
    scorecard, decision_payload = eval_pack.decide_final_status(
        source_gate=source_gate,
        scenario_catalog=scenario_catalog,
        rubric_validation=rubric_validation,
        metrics=eval_metrics["metrics"],
        kb_boundary_eval=kb_boundary_eval,
        no_runtime_authority_gate=no_runtime_authority_gate,
        no_mutation_proof=no_mutation_proof,
        artifact_hygiene_passed=artifact_hygiene_passed,
        docs_sync=docs_sync,
    )
    eval_results_payload["final_status"] = scorecard["final_status"]
    eval_results_payload["decision"] = scorecard["decision"]
    _write_json(out_dir / "response_quality_eval_results.json", eval_results_payload)
    _write_json(out_dir / "diagnostic_center_response_quality_eval_scorecard.json", scorecard)

    return {
        "status": scorecard["final_status"],
        "decision": scorecard["decision"],
        "scorecard": scorecard,
        "decision_payload": decision_payload,
        "preflight": preflight,
        "encoding_report": encoding_report,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PRD-046.1.17 Diagnostic Center response quality eval pack.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--source-dir", default="TO_DO_LIST/logs/PRD-046.1.16")
    parser.add_argument("--scenarios", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json")
    parser.add_argument("--rubric", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json")
    parser.add_argument("--response-candidates", default="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json")
    parser.add_argument("--output-dir", default="TO_DO_LIST/logs/PRD-046.1.17")
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
