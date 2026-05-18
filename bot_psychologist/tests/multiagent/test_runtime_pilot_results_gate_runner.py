from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_gate_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.20",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "needs_fix", "failed"}
    for name in (
        "source_gate.json",
        "execution_evidence_review.json",
        "rollback_evidence_review.json",
        "normal_user_no_effect_review.json",
        "quality_delta_review.json",
        "safety_kb_boundary_review.json",
        "trace_sanitization_review.json",
        "artifact_hygiene_review.json",
        "encoding_warning_review.json",
        "no_mutation_review.json",
        "runtime_pilot_results_risk_register.json",
        "runtime_pilot_results_decision_gate.json",
        "runtime_pilot_results_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
