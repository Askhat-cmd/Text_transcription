from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_execution_gate as runner


def test_supervised_execution_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "prd_046_1_9"
    result = runner.run(
        argparse.Namespace(
            plan_dir="TO_DO_LIST/logs/PRD-046.1.8",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "supervised_execution_manifest.json",
        "supervised_execution_trace_samples.json",
        "supervised_execution_baseline_vs_test_apply.json",
        "supervised_execution_normal_user_no_effect.json",
        "supervised_execution_rollback_proof.json",
        "supervised_execution_observability_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
