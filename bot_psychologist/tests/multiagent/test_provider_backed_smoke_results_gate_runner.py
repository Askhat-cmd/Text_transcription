from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_provider_backed_smoke_results_gate as runner


def test_provider_backed_smoke_results_gate_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.23",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "passed_with_warnings", "failed"}
    for name in (
        "source_gate.json",
        "provider_execution_evidence_review.json",
        "provider_budget_review.json",
        "normal_user_no_effect_review.json",
        "quality_consolidation_review.json",
        "safety_kb_boundary_consolidation.json",
        "provider_output_sanitization_consolidation.json",
        "trace_sanitization_consolidation.json",
        "rollback_evidence_review.json",
        "botdb_stability_review.json",
        "hard_stop_absence_review.json",
        "no_mutation_review.json",
        "provider_backed_results_risk_register.json",
        "provider_backed_results_decision_gate.json",
        "provider_backed_smoke_results_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name

