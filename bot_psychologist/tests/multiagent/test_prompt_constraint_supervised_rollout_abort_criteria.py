from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_rollout_plan as runner


def test_abort_criteria_contains_required_hard_conditions(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.7",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_rollout_abort_criteria.json").read_text(encoding="utf-8"))
    hard = set(payload["hard_abort_conditions"])
    assert payload["ready"] is True
    assert "normal_user_apply_count > 0" in hard
    assert "rollback_failure_count > 0" in hard
    assert "production_mutation_detected=true" in hard
    assert "provider_called_by_gate_count > 0" in hard
