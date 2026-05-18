from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_execution as runner


def test_runtime_pilot_execution_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.19",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "failed", "passed_with_quality_warnings"}
    for name in (
        "source_gate.json",
        "preflight_gate.json",
        "execution_manifest.json",
        "toggle_state_before.json",
        "rollback_precheck.json",
        "pilot_operator_trace_samples_sanitized.json",
        "normal_user_control_trace_samples_sanitized.json",
        "limited_live_smoke_results.json",
        "baseline_vs_pilot_quality_delta.json",
        "safety_kb_boundary_gate.json",
        "trace_sanitization_gate.json",
        "rollback_postcheck.json",
        "hard_stop_evaluation.json",
        "monitoring_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name

