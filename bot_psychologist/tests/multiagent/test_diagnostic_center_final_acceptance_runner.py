from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_acceptance as runner


def test_final_acceptance_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            source_dir="TO_DO_LIST/logs/PRD-046.1.15",
            repo_root=".",
            output_dir=str(out_dir),
            reports_dir=str(reports_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "failed"}
    for name in (
        "final_acceptance_source_gate.json",
        "runtime_governance_boundary_matrix.json",
        "permanent_regression_gate_confirmation.json",
        "prompt_constraint_conservative_baseline_gate.json",
        "normal_user_no_effect_gate.json",
        "kb_governance_boundary_gate.json",
        "trace_sanitization_gate.json",
        "runtime_governance_closure_decision.json",
        "diagnostic_center_v1_final_acceptance_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
