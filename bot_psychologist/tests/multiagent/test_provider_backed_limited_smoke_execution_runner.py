from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_provider_backed_limited_smoke_execution as runner


def test_provider_backed_limited_smoke_execution_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            admin_base_url="http://127.0.0.1:8003",
            source_dir="TO_DO_LIST/logs/PRD-046.1.22",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            provider_mode="mock",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "passed_with_warnings", "failed", "blocked"}
    for name in (
        "source_gate.json",
        "live_dependency_preflight.json",
        "provider_availability_preflight.json",
        "toggle_state_before.json",
        "rollback_precheck.json",
        "execution_manifest.json",
        "provider_call_budget.json",
        "pilot_operator_provider_backed_execution.json",
        "pilot_operator_trace_samples_sanitized.json",
        "normal_user_control_execution.json",
        "normal_user_control_trace_samples_sanitized.json",
        "provider_output_sanitization_review.json",
        "quality_review.json",
        "safety_kb_boundary_review.json",
        "trace_sanitization_review.json",
        "rollback_postcheck.json",
        "hard_stop_evaluation.json",
        "no_mutation_proof.json",
        "provider_backed_limited_smoke_execution_scorecard.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
