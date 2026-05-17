from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_quality_gate as runner


def test_gate_verification_has_no_kb_or_allowlist_exposure(tmp_path: Path) -> None:
    out_dir = tmp_path / "quality_gate"
    runner.run(
        argparse.Namespace(
            input_dir="TO_DO_LIST/logs/PRD-046.1.6",
            output_dir=str(out_dir),
            strict=True,
            allow_missing_runtime_samples="false",
            max_quality_regression_count=0,
            max_rollback_failure_count=0,
            max_safety_violation_count=0,
        )
    )
    payload = json.loads((out_dir / "prompt_constraint_pilot_gate_verification.json").read_text(encoding="utf-8"))
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["internal_only_exposure_count"] == 0
    assert payload["not_for_direct_quote_violation_count"] == 0
    assert payload["normal_user_apply_count"] == 0
    assert payload["provider_called_by_gate_count"] == 0

