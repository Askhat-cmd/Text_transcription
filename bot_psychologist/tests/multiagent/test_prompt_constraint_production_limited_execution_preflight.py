from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_execution_preflight_passed(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "production_limited_preflight_result.json").read_text(encoding="utf-8"))
    assert payload["source_plan_gate_passed"] is True
    assert payload["operator_checklist_complete"] is True
    assert payload["monitoring_plan_ready"] is True
    assert payload["rollback_plan_ready"] is True
    assert payload["abort_criteria_ready"] is True
    assert payload["allowlist_ready"] is True
    assert payload["target_user_count_allowed"] is True
    assert payload["normal_user_controls_ready"] is True
    assert payload["config_defaults_conservative"] is True
    assert payload["force_disabled_available"] is True
    assert payload["preflight_passed"] is True
