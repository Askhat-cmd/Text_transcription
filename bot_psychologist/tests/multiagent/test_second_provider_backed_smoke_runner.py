from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_second_provider_backed_limited_smoke as runner


def test_second_provider_backed_smoke_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            admin_base_url="http://127.0.0.1:8003",
            source_dir="TO_DO_LIST/logs/PRD-046.1.24",
            reports_dir="TO_DO_LIST/reports",
            output_dir=str(out_dir),
            fixture_path="bot_psychologist/tests/fixtures/diagnostic_center_second_provider_backed_smoke_cases.json",
            provider_mode="mock",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked"}
    for name in (
        "source_gate.json",
        "botdb_live_preflight.json",
        "rollback_precheck.json",
        "execution_manifest.json",
        "provider_budget_gate.json",
        "sanitized_provider_trace.json",
        "normal_user_no_effect_gate.json",
        "quality_micro_shift_gate.json",
        "safety_kb_boundary_gate.json",
        "trace_sanitization_gate.json",
        "rollback_postcheck.json",
        "botdb_stability_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene.json",
        "decision_gate.json",
        "scorecard.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
