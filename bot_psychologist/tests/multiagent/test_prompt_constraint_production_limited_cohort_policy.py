from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_rollout_plan as runner


def test_cohort_policy_limits_and_flags(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(source_dir="TO_DO_LIST/logs/PRD-046.1.11", output_dir=str(out_dir), strict=True))
    payload = json.loads((out_dir / "production_limited_cohort_policy.json").read_text(encoding="utf-8"))
    assert payload["execution_allowed_in_this_prd"] is False
    assert payload["max_initial_real_user_count"] <= 1
    assert payload["max_total_users_in_first_execution_prd"] <= 2
    assert payload["allowlist_required"] is True
    assert payload["manual_operator_approval_required"] is True
    assert payload["automatic_enrollment_allowed"] is False
    assert payload["normal_user_default_path_unchanged"] is True
