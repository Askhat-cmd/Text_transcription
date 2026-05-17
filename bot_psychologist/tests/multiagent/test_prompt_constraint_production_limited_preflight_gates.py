from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_preflight_gates_structure(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_preflight_gates.json").read_text(encoding="utf-8"))
    required = payload["required_before_execution"]
    assert required["source_consolidation_passed"] is True
    assert required["operator_checklist_completed"] is True
    assert required["rollback_plan_reviewed"] is True
    assert required["monitoring_plan_ready"] is True
    assert required["abort_criteria_ready"] is True
    assert required["config_default_conservative"] is True
    assert required["force_disabled_rollback_available"] is True
    assert "source_consolidation_missing" in payload["blocked_if"]
