from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_completion_gate as runner  # noqa: E402


def test_prd_046_1_37_runner_outputs_required_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner.gate,
        "build_runtime_readiness_final_gate",
        lambda **_: (
            {
                "runtime_readiness_final_gate": "passed",
                "admin_runtime_endpoint_status_code": 200,
                "backend_adaptive_endpoint_status": 200,
                "backend_debug_trace_endpoint_status": 200,
                "botdb_status_code": 200,
                "botdb_query_status_code": 200,
                "web_ui_status_code": 200,
            },
            {"schema_version": "admin_effective_runtime_v1"},
        ),
    )
    monkeypatch.setattr(
        runner.gate,
        "run_actual_live_creator_smoke",
        lambda **_: (
            {
                "gate": "passed",
                "actual_live_cases_total": 5,
                "actual_live_cases_passed": 5,
                "diagnostic_center_active_for_creator_count": 5,
                "diagnostic_center_trace_present_count": 5,
                "cases": [],
            },
            [],
        ),
    )
    monkeypatch.setattr(
        runner.gate,
        "build_rollback_hard_stop_final_gate",
        lambda **_: {"rollback_hard_stop_final_gate": "passed"},
    )
    monkeypatch.setattr(
        runner.gate,
        "run_normal_user_final_no_effect_gate",
        lambda **_: {
            "normal_user_final_no_effect_gate": "passed",
            "diagnostic_center_live_authority_applied": False,
        },
    )
    monkeypatch.setattr(
        runner.gate,
        "build_trace_sanitization_final_gate",
        lambda *_: {"trace_sanitization_final_gate": "passed"},
    )
    monkeypatch.setattr(
        runner.encoding_validator,
        "run",
        lambda _args: {"final_status": "passed", "schema_version": "artifact_encoding_hygiene_report_v1"},
    )

    out_dir = tmp_path / "out"
    docs_dir = tmp_path / "docs"
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            repo_root=".",
            docs_dir=str(docs_dir),
            reports_dir=str(reports_dir),
            output_dir=str(out_dir),
            backend_base_url="http://localhost:8001",
            botdb_base_url="http://localhost:8003",
            web_ui_base_url="http://localhost:3000",
            api_key="dev-key-001",
            creator_user_id="user_1772172411219_kamh0",
            normal_user_id="user_normal_control_prd_046_1_37",
            strict=True,
        )
    )
    assert result["status"] in {"completed", "blocked", "evidence_incomplete"}
    for name in (
        "source_gate.json",
        "evidence_provenance_audit.json",
        "runtime_readiness_final_gate.json",
        "actual_live_creator_smoke.json",
        "admin_runtime_controls_final_gate.json",
        "rollback_hard_stop_final_gate.json",
        "normal_user_final_no_effect_gate.json",
        "rag_behavior_final_regression_gate.json",
        "trace_sanitization_final_gate.json",
        "provider_budget_final_gate.json",
        "no_mutation_final_proof.json",
        "artifact_encoding_hygiene_report.json",
        "diagnostic_center_final_completion_scorecard.json",
        "test_command_output.txt",
    ):
        assert (out_dir / name).exists(), name
