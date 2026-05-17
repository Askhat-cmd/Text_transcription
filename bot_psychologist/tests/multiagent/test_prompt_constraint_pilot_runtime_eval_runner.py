from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_prompt_constraint_pilot_runtime_eval as runner


def test_prompt_constraint_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/prompt_constraint_pilot_runtime_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 45


def test_prompt_constraint_eval_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "prompt_constraint_eval"
    result = runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/prompt_constraint_pilot_runtime_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] in {"passed", "failed"}
    for name in (
        "prompt_constraint_pilot_runtime_eval.json",
        "prompt_constraint_pilot_runtime_scorecard.json",
        "prompt_constraint_pilot_runtime_smoke.json",
        "prompt_constraint_pilot_runtime_trace_samples.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists()

