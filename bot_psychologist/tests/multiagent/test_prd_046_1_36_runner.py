from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_creator_live_pilot_acceptance as runner  # noqa: E402


def test_prd_046_1_36_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            reports_dir="TO_DO_LIST/reports",
            docs_dir="docs",
            output_dir=str(out_dir),
            backend_base_url="http://localhost:8001",
            botdb_base_url="http://localhost:8003",
            web_ui_base_url="http://localhost:3000",
            creator_user_id="user_1772172411219_kamh0",
            normal_user_id="user_normal_control_prd_046_1_36",
            fixture_path="bot_psychologist/tests/fixtures/prd_046_1_36_creator_live_pilot_cases.json",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked"}
    for name in (
        "source_gate.json",
        "runtime_readiness_gate.json",
        "admin_runtime_controls_acceptance.json",
        "creator_live_pilot_acceptance.json",
        "diagnostic_center_trace_acceptance.json",
        "rollback_force_disabled_proof.json",
        "normal_user_no_effect_gate.json",
        "rag_and_behavior_regression_gate.json",
        "trace_sanitization_gate.json",
        "provider_budget_gate.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "prd_046_1_36_scorecard.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name

