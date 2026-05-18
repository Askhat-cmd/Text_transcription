from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_runtime_pilot_readiness as runner


def test_runtime_pilot_cohort_policy_is_conservative(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            repo_root=".",
            source_dir="TO_DO_LIST/logs/PRD-046.1.18",
            output_dir=str(out_dir),
            reports_dir="TO_DO_LIST/reports",
            strict=True,
        )
    )
    policy = json.loads((out_dir / "cohort_policy.json").read_text(encoding="utf-8"))
    assert policy["max_initial_cohort_size"] == 1
    assert policy["normal_user_control_count"] >= 2
    assert policy["normal_user_apply_allowed"] is False
