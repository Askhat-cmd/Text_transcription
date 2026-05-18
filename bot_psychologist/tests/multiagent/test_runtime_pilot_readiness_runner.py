from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_readiness as runner


def test_runtime_pilot_readiness_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.18",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "failed", "passed_with_quality_warnings"}
    for name in (
        "source_gate.json",
        "pilot_scope.json",
        "cohort_policy.json",
        "toggle_matrix.json",
        "runtime_preflight_requirements.json",
        "limited_live_smoke_plan.json",
        "rollback_first_runbook.json",
        "hard_stop_criteria.json",
        "monitoring_artifact_contract.json",
        "normal_user_guard.json",
        "kb_governance_guard.json",
        "trace_sanitization_guard.json",
        "runtime_pilot_readiness_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
