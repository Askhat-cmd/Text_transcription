from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


def test_aggregate_metrics_from_two_cycles(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            source_a_dir="TO_DO_LIST/logs/PRD-046.1.9",
            source_b_dir="TO_DO_LIST/logs/PRD-046.1.10",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_consolidation_aggregate_metrics.json").read_text(encoding="utf-8"))
    assert payload["cycles_total"] == 2
    assert payload["cycles_passed"] == 2
    assert payload["total_test_apply_applied_count"] == 9
    assert payload["total_cases_compared"] == 9
    assert payload["max_cohort_size_seen"] == 6
    assert payload["normal_user_apply_total"] == 0
    assert payload["default_off_user_path_effect_total"] == 0
    assert payload["rollback_failure_total"] == 0
    assert payload["candidate_weaker_than_baseline_total"] == 0
    assert payload["safety_regression_total"] == 0
    assert payload["kb_policy_regression_total"] == 0
    assert payload["prompt_bloat_regression_total"] == 0
    assert payload["constraint_conflict_regression_total"] == 0
    assert payload["raw_kb_text_exposure_total"] == 0
    assert payload["internal_only_exposure_total"] == 0
    assert payload["not_for_direct_quote_violation_total"] == 0
    assert payload["provider_called_total"] == 0
    assert payload["production_mutation_detected_any"] is False
