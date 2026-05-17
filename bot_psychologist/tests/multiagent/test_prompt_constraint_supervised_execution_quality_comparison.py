from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_execution_gate as runner


def test_baseline_vs_test_apply_comparison_is_clean(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            plan_dir="TO_DO_LIST/logs/PRD-046.1.8",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_execution_baseline_vs_test_apply.json").read_text(encoding="utf-8"))
    assert payload["cases_compared"] >= 3
    assert payload["test_apply_applied_count"] > 0
    assert payload["candidate_weaker_than_baseline_count"] == 0
    assert payload["safety_regression_count"] == 0
    assert payload["kb_policy_regression_count"] == 0
    assert payload["prompt_bloat_regression_count"] == 0
    assert payload["constraint_conflict_regression_count"] == 0
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["provider_called_by_execution_count"] == 0
