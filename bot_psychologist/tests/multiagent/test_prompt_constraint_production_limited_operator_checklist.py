from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


REQUIRED_IDS = {
    "confirm_scope",
    "confirm_allowlist",
    "confirm_force_disabled_start",
    "capture_baseline_no_mutation",
    "enable_for_limited_window_only",
    "capture_trace_samples",
    "run_normal_user_control",
    "rollback_force_disabled",
    "compare_quality",
    "final_decision",
}


def test_operator_checklist_contains_required_steps(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_operator_checklist.json").read_text(encoding="utf-8"))
    ids = {item["id"] for item in payload["checklist"]}
    assert REQUIRED_IDS.issubset(ids)
    assert all(item["required"] is True for item in payload["checklist"])
