from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_quality_gate as runner


def test_rollback_toggle_matrix_has_zero_failures(tmp_path: Path) -> None:
    out_dir = tmp_path / "quality_gate"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.6",
            output_dir=str(out_dir),
            strict=True,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    payload = json.loads((out_dir / "rollback_toggle_matrix.json").read_text(encoding="utf-8"))
    assert payload["rollback_failure_count"] == 0
    assert payload["stale_apply_after_force_disabled_count"] == 0
    assert payload["rollback_priority_preserved"] is True

