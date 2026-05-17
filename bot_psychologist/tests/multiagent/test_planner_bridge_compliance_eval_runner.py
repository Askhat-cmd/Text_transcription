from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_planner_bridge_compliance_shadow_eval as runner


def test_compliance_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/planner_bridge_compliance_shadow_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 30


def test_compliance_eval_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "compliance_shadow_eval"
    result = runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/planner_bridge_compliance_shadow_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] in {"passed", "done_with_shadow_blocker"}
    for name in (
        "planner_bridge_compliance_shadow_eval.json",
        "planner_bridge_compliance_shadow_scorecard.json",
        "planner_bridge_compliance_trace_samples.json",
        "planner_bridge_compliance_runtime_smoke.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists()

