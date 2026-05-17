from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_monitoring_scorecard_has_expected_fields(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "production_limited_monitoring_scorecard.json").read_text(encoding="utf-8"))
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "continue_limited"
    assert payload["source_plan_gate_passed"] is True
    assert payload["execution_window_count"] == 1
    assert payload["target_user_count"] == 1
    assert payload["target_user_limit_respected"] is True
    assert payload["production_limited_apply_count"] >= 1
    assert payload["normal_user_apply_count"] == 0
    assert payload["rollback_failure_count"] == 0
    assert payload["safety_regression_count"] == 0
    assert payload["kb_policy_regression_count"] == 0
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["provider_called_by_execution_count"] == 0
    assert payload["trace_sanitization_failed"] is False
