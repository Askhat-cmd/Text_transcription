from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_planner_bridge_writer_contract_pilot_eval as runner


def test_writer_contract_pilot_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/planner_bridge_writer_contract_pilot_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 36


def test_writer_contract_pilot_eval_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "writer_contract_pilot_eval"
    result = runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/planner_bridge_writer_contract_pilot_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] in {"passed", "done_with_pilot_blocker", "failed_safety_violation"}
    for name in (
        "planner_bridge_writer_contract_pilot_eval.json",
        "planner_bridge_writer_contract_pilot_scorecard.json",
        "planner_bridge_writer_contract_pilot_trace_samples.json",
        "planner_bridge_writer_contract_pilot_runtime_smoke.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists()
