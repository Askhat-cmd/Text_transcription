from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_supervised_consolidation_gate as runner


def test_reproducibility_passed_for_clean_cycles(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(
        argparse.Namespace(
            source_a_dir="TO_DO_LIST/logs/PRD-046.1.9",
            source_b_dir="TO_DO_LIST/logs/PRD-046.1.10",
            output_dir=str(out_dir),
            strict=True,
        )
    )
    payload = json.loads((out_dir / "supervised_consolidation_reproducibility.json").read_text(encoding="utf-8"))
    assert payload["both_cycles_passed"] is True
    assert payload["both_cycles_continue_supervised"] is True
    assert payload["normal_user_no_effect_repeated"] is True
    assert payload["rollback_success_repeated"] is True
    assert payload["no_safety_regression_repeated"] is True
    assert payload["no_kb_regression_repeated"] is True
    assert payload["no_prompt_bloat_repeated"] is True
    assert payload["no_constraint_conflict_repeated"] is True
    assert payload["no_raw_kb_exposure_repeated"] is True
    assert payload["provider_free_repeated"] is True
    assert payload["no_mutation_repeated"] is True
    assert payload["reproducibility_passed"] is True
