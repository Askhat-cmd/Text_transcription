from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_response_quality_calibration as runner


def test_expanded_scenario_and_candidate_catalog_requirements(tmp_path: Path) -> None:
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
    scenarios = json.loads((out_dir / "expanded_scenario_catalog.json").read_text(encoding="utf-8"))
    candidates = json.loads((out_dir / "expanded_candidate_catalog.json").read_text(encoding="utf-8"))
    assert scenarios["scenario_count"] >= 34
    assert scenarios["required_scenario_groups_present"] is True
    assert candidates["candidate_profile_count"] >= 8
    assert candidates["all_required_candidate_profiles_present"] is True
