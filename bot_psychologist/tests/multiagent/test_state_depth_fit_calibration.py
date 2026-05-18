from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_calibration as runner


def test_state_depth_fit_calibration_threshold(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_logs_dir="TO_DO_LIST/logs/PRD-046.1.17",
            source_reports_dir="TO_DO_LIST/reports",
            scenarios="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json",
            rubric="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json",
            response_candidates="bot_psychologist/tests/fixtures/diagnostic_center_response_quality_response_candidates.json",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    scorecard = json.loads((out_dir / "diagnostic_center_response_quality_calibration_scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["state_depth_fit_weak_detection_rate"] >= 0.90
