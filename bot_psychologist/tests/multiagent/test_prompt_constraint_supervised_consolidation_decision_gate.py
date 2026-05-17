from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


def test_decision_gate_prepares_limited_rollout_plan(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            source_a_dir="TO_DO_LIST/logs/PRD-046.1.9",
            source_b_dir="TO_DO_LIST/logs/PRD-046.1.10",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_consolidation_rollout_decision_gate.json").read_text(encoding="utf-8"))
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "prepare_production_limited_rollout_plan"
    assert payload["source_cycles_passed"] is True
    assert payload["aggregate_metrics_passed"] is True
    assert payload["reproducibility_passed"] is True
    assert payload["risk_register_has_blockers"] is False
    assert payload["normal_user_apply_total"] == 0
    assert payload["rollback_failure_total"] == 0
    assert payload["safety_regression_total"] == 0
    assert payload["kb_policy_regression_total"] == 0
    assert payload["raw_kb_text_exposure_total"] == 0
    assert payload["provider_called_total"] == 0
    assert payload["production_mutation_detected_any"] is False
