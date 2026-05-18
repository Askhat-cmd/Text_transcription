from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_results_gate as runner


def test_production_limited_results_gate_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.13", output_dir=str(out_dir), strict=True))
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "production_limited_results_manifest.json",
        "production_limited_quality_summary.json",
        "production_limited_rollback_summary.json",
        "production_limited_normal_user_summary.json",
        "production_limited_trace_sanitization_summary.json",
        "production_limited_post_run_risk_register.json",
        "production_limited_results_decision_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
