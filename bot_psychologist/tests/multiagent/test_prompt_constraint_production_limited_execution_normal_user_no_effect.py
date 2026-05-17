from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_normal_user_no_effect(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "production_limited_normal_user_no_effect.json").read_text(encoding="utf-8"))
    assert payload["normal_user_cases_total"] == 2
    assert payload["normal_user_apply_count"] == 0
    assert payload["normal_user_prompt_changed_by_pilot_count"] == 0
    assert payload["normal_user_final_answer_changed_by_pilot_count"] == 0
    assert payload["default_off_user_path_effect_count"] == 0
