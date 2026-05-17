from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_continuation_gate as runner


def test_scenario_coverage_has_required_six_scenarios(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.9", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "supervised_continuation_scenario_coverage.json").read_text(encoding="utf-8"))
    assert len(payload["required_scenarios"]) == 6
    assert payload["covered_scenarios_count"] == 6
    assert payload["coverage_passed"] is True
    assert payload["missing_scenarios"] == []
