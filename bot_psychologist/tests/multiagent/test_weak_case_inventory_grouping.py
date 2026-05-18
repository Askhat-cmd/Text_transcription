from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_calibration as runner


def test_weak_case_inventory_grouping_contains_required_dimensions(tmp_path: Path) -> None:
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
    inventory = json.loads((out_dir / "weak_case_inventory.json").read_text(encoding="utf-8"))
    dimensions = {item["dimension"] for item in inventory["dimension_group_plans"]}
    assert {"state_depth_fit", "non_directiveness", "non_bookishness", "kb_boundary_respect"}.issubset(dimensions)
