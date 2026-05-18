from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_results_gate as runner


def test_runtime_pilot_results_quality_delta_review_expected_values(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.20",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "quality_delta_review.json").read_text(encoding="utf-8"))
    assert payload["quality_delta_status"] == "passed"
    assert payload["candidate_weaker_than_baseline_count"] == 0
    assert payload["state_depth_fit_regression_count"] == 0
    assert payload["non_directiveness_regression_count"] == 0
    assert payload["non_bookishness_regression_count"] == 0
    assert payload["kb_boundary_regression_count"] == 0
    assert payload["safety_regression_count"] == 0
    assert payload["prompt_bloat_blocker_count"] == 0
    assert payload["constraint_conflict_count"] == 0
    assert payload["quality_gate_decision"] == "passed"
