from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_contract_audit as audit_runner


def test_eval_cases_fixture_has_minimum_required_cases() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/diagnostic_center_v1_cases.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 10


def test_contract_audit_runner_passes_on_fixture(tmp_path: Path) -> None:
    out_dir = tmp_path / "audit_out"
    result = audit_runner.run(
        argparse.Namespace(
            cases_file="bot_psychologist/tests/fixtures/diagnostic_center_v1_cases.json",
            out_dir=str(out_dir),
        )
    )
    assert result["status"] == "passed"
    assert result["scorecard"]["contract_pass_rate"] == 1.0
    assert (out_dir / "diagnostic_center_contract_audit.json").exists()
    assert (out_dir / "diagnostic_center_eval_scorecard.json").exists()
    assert (out_dir / "diagnostic_center_trace_samples.json").exists()
    assert (out_dir / "no_mutation_proof.json").exists()
