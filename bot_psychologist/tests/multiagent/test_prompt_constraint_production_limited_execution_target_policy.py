from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_production_limited_execution_gate as runner


def test_execution_target_policy_single_target_user(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id=None))
    payload = json.loads((out_dir / "production_limited_execution_manifest.json").read_text(encoding="utf-8"))
    assert payload["execution_window_count"] == 1
    assert payload["target_user_count"] == 1
    assert payload["real_user_count"] == 0
    assert payload["synthetic_operator_user_count"] == 1
    assert payload["target_user_id"] == "prod_limited_operator_001"
    assert payload["automatic_background_execution"] is False


def test_operator_user_id_is_sanitized_and_single(tmp_path: Path) -> None:
    out_dir = tmp_path / "out_op"
    runner.run(argparse.Namespace(plan_dir="TO_DO_LIST/logs/PRD-046.1.12", output_dir=str(out_dir), strict=True, operator_user_id="operator_safe_01"))
    payload = json.loads((out_dir / "production_limited_execution_manifest.json").read_text(encoding="utf-8"))
    assert payload["target_user_count"] == 1
    assert payload["real_user_count"] == 1
    assert payload["synthetic_operator_user_count"] == 0
    assert payload["target_user_id"] == "operator_safe_01"
