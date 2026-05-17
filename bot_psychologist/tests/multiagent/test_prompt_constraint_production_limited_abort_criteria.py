from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_abort_criteria_contains_hard_abort_conditions(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_abort_criteria.json").read_text(encoding="utf-8"))
    hard = payload["hard_abort_if"]
    assert "normal_user_apply_count > 0" in hard
    assert "rollback_failure_count > 0" in hard
    assert "safety_regression_count > 0" in hard
    assert "kb_policy_regression_count > 0" in hard
    assert "raw_kb_text_exposure_count > 0" in hard
    assert "internal_only_exposure_count > 0" in hard
    assert "production_mutation_detected=true" in hard
    assert "trace_sanitization_failed=true" in hard
    assert len(payload["warning_if"]) > 0
