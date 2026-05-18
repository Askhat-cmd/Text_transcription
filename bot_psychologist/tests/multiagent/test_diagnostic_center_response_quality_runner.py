from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_eval as runner


def test_response_quality_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.16",
            scenarios="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json",
            rubric="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json",
            response_candidates="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json",
            output_dir=str(out_dir),
            reports_dir=str(reports_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "passed_with_quality_warnings", "failed"}
    for name in (
        "source_gate.json",
        "response_quality_scenario_catalog.json",
        "response_quality_rubric_validation.json",
        "response_quality_eval_results.json",
        "response_quality_dimension_scorecard.json",
        "response_quality_weak_case_queue.json",
        "kb_internal_lens_response_boundary_eval.json",
        "no_runtime_authority_expansion_gate.json",
        "diagnostic_center_response_quality_eval_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
