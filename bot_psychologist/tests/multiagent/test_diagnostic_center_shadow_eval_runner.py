from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_shadow_eval as shadow_eval


def test_shadow_fixture_has_minimum_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/diagnostic_center_shadow_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 10


def test_shadow_eval_runner_generates_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "shadow_eval"
    result = shadow_eval.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/diagnostic_center_shadow_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] in {
        "passed",
        "done_with_shadow_divergence_warnings",
        "done_with_shadow_blocker",
        "failed_safety_violation",
    }
    for name in (
        "diagnostic_center_shadow_eval.json",
        "diagnostic_center_shadow_divergence_scorecard.json",
        "diagnostic_center_shadow_trace_samples.json",
        "diagnostic_center_shadow_runtime_smoke.json",
        "no_mutation_proof.json",
    ):
        assert (out_dir / name).exists()
