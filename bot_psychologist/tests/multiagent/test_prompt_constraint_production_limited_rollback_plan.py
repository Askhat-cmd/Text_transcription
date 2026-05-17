from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_rollback_plan_force_disabled_priority(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_rollback_plan.json").read_text(encoding="utf-8"))
    assert payload["rollback_priority"] == "force_disabled_absolute_priority"
    assert payload["primary_rollback"]["set_PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED"] is True
    assert payload["primary_rollback"]["expected_apply_count_after_rollback"] == 0
    assert payload["secondary_rollback"]["set_PROMPT_CONSTRAINT_PILOT_ENABLED"] is False
    assert payload["secondary_rollback"]["clear_allowlist"] is True
    assert payload["verification"]["stale_apply_after_force_disabled_must_be"] == 0
