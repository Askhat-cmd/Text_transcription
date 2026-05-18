from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_execution as runner


def test_runtime_pilot_quality_delta_passes(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.19",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    payload = json.loads((out_dir / "baseline_vs_pilot_quality_delta.json").read_text(encoding="utf-8"))
    assert payload["quality_delta_status"] == "passed"
    assert payload["candidate_weaker_than_baseline_count"] == 0

