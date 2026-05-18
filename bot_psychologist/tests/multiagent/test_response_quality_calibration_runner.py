from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_calibration as runner


def test_response_quality_calibration_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_logs_dir="TO_DO_LIST/logs/PRD-046.1.17",
            source_reports_dir="TO_DO_LIST/reports",
            scenarios="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json",
            rubric="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json",
            response_candidates="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "passed_with_quality_warnings", "failed"}
    for name in (
        "source_gate.json",
        "weak_case_inventory.json",
        "calibration_plan.json",
        "expanded_scenario_catalog.json",
        "expanded_candidate_catalog.json",
        "calibrated_rubric_validation.json",
        "calibrated_response_quality_eval_results.json",
        "calibrated_dimension_scorecard.json",
        "weak_case_closure_report.json",
        "kb_boundary_calibration_report.json",
        "no_runtime_authority_expansion_gate.json",
        "diagnostic_center_response_quality_calibration_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
