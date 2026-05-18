from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_stabilization_cleanup as runner


def test_stabilization_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            source_dir="TO_DO_LIST/logs/PRD-046.1.14",
            repo_root=".",
            output_dir=str(out_dir),
            reports_dir=str(reports_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "stabilization_source_gate.json",
        "diagnostic_center_module_inventory.json",
        "diagnostic_center_module_classification.json",
        "diagnostic_center_regression_gate_catalog.json",
        "diagnostic_center_cleanup_plan.json",
        "diagnostic_center_archive_manifest.json",
        "diagnostic_center_stabilization_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
