from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_planner_bridge_eval as runner


def test_planner_bridge_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/diagnostic_center_planner_bridge_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 24


def test_planner_bridge_eval_runner_outputs_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "planner_bridge_eval"
    result = runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/diagnostic_center_planner_bridge_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] == "passed"
    assert result["scorecard"]["cases_total"] >= 24
    assert result["scorecard"]["cases_total"] == result["scorecard"]["cases_passed"]
    assert result["scorecard"]["planner_bridge_apply_to_writer_count"] == 0
    for name in (
        "shadow_divergence_calibration_audit.json",
        "shadow_divergence_calibration_scorecard.json",
        "planner_bridge_contract_eval.json",
        "planner_bridge_trace_samples.json",
        "no_mutation_proof.json",
    ):
        assert (out_dir / name).exists()

