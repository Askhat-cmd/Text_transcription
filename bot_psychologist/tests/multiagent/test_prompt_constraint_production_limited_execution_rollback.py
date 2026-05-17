from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_rollback_proof_passed(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "production_limited_rollback_proof.json").read_text(encoding="utf-8"))
    assert payload["rollback_cases_total"] == 1
    assert payload["rollback_cases_passed"] == 1
    assert payload["rollback_failure_count"] == 0
    assert payload["stale_apply_after_force_disabled_count"] == 0
    assert payload["force_disabled_absolute_priority"] is True
    assert payload["allowlisted_target_apply_after_rollback"] == 0
