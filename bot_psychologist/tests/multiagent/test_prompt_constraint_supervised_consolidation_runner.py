from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


def test_supervised_consolidation_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "prd_046_1_11"
    result = runner.run(
        argparse.Namespace(
            source_a_dir="TO_DO_LIST/logs/PRD-046.1.9",
            source_b_dir="TO_DO_LIST/logs/PRD-046.1.10",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked", "needs_hotfix"}
    for name in (
        "supervised_consolidation_manifest.json",
        "supervised_consolidation_aggregate_metrics.json",
        "supervised_consolidation_reproducibility.json",
        "supervised_consolidation_risk_register.json",
        "supervised_consolidation_rollout_decision_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists(), name
