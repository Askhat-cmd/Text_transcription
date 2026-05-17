from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_monitoring_plan_contains_safety_kb_privacy_metrics(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_monitoring_plan.json").read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    assert "normal_user_apply_count" in metrics
    assert "safety_regression_count" in metrics
    assert "kb_policy_regression_count" in metrics
    assert "raw_kb_text_exposure_count" in metrics
    assert "internal_only_exposure_count" in metrics
    assert "not_for_direct_quote_violation_count" in metrics
    trace = payload["trace_requirements"]
    assert trace["sanitized_trace_only"] is True
    assert trace["raw_prompt_forbidden"] is True
    assert trace["raw_kb_text_forbidden"] is True
    assert trace["private_user_text_forbidden"] is True
