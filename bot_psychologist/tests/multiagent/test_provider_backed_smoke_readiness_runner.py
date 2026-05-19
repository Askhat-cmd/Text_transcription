from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_provider_backed_smoke_readiness as runner


def test_provider_backed_smoke_readiness_runner_outputs_required_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            reports_dir="TO_DO_LIST/reports",
            logs_root="TO_DO_LIST/logs",
            output_dir=str(out_dir),
            admin_base_url="http://127.0.0.1:8003",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "failed", "blocked"}
    for name in (
        "diagnostic_center_source_gate.json",
        "botdb_recovery_source_gate.json",
        "live_dependency_readiness_gate.json",
        "provider_readiness_policy.json",
        "provider_backed_cohort_policy.json",
        "provider_backed_toggle_matrix.json",
        "provider_backed_smoke_scenario_pack.json",
        "normal_user_control_plan.json",
        "provider_backed_rollback_first_runbook.json",
        "provider_backed_hard_stop_criteria.json",
        "provider_backed_kb_boundary_contract.json",
        "provider_backed_trace_sanitization_contract.json",
        "provider_backed_execution_manifest_template.json",
        "provider_backed_limited_smoke_readiness_scorecard.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
