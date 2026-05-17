from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_production_limited_execution_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None)
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "production_limited_execution_manifest.json",
        "production_limited_preflight_result.json",
        "production_limited_trace_samples.json",
        "production_limited_baseline_vs_test_apply.json",
        "production_limited_normal_user_no_effect.json",
        "production_limited_rollback_proof.json",
        "production_limited_monitoring_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
