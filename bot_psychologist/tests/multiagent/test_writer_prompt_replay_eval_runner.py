from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_writer_prompt_replay_eval as runner


def test_replay_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/writer_prompt_replay_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 40


def test_replay_eval_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "writer_prompt_replay_eval"
    result = runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/writer_prompt_replay_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] in {"passed", "done_with_replay_blocker", "failed_safety_violation"}
    for name in (
        "writer_prompt_replay_eval.json",
        "writer_prompt_replay_scorecard.json",
        "writer_prompt_replay_trace_samples.json",
        "writer_prompt_replay_runtime_smoke.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
    ):
        assert (out_dir / name).exists()
