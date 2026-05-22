from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_diagnostic_center_final_completion_hf1 as runner  # noqa: E402


def _write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def test_prd_046_1_37_hf1_runner_writes_artifacts(tmp_path: Path, monkeypatch) -> None:
    _write(
        tmp_path / "TO_DO_LIST/logs/PRD-046.1.37/diagnostic_center_final_completion_scorecard.json",
        json.dumps(
            {
                "final_status": "blocked",
                "decision": "blocked_runtime_readiness",
                "runtime_readiness_final_gate": "blocked",
                "actual_live_creator_smoke_gate": "blocked",
                "no_mutation_final_proof": "passed",
                "artifact_encoding_hygiene": "passed",
                "broad_rollout_allowed": False,
                "production_ready": False,
                "normal_user_activation_allowed": False,
                "all_users_mode_enabled": False,
            }
        ),
    )
    _write(tmp_path / "TO_DO_LIST/reports/PRD-046.1.37_IMPLEMENTATION_REPORT.md", "ok")
    _write(tmp_path / "TO_DO_LIST/logs/PRD-046.1.37/runtime_readiness_final_gate.json", "{}")
    _write(tmp_path / "TO_DO_LIST/logs/PRD-046.1.37/actual_live_creator_smoke.json", "{}")
    _write(tmp_path / "docs/PROJECT_STATE.md", "# Project State\n")
    for rel in (
        "Bot_data_base/data/processed/all_blocks_merged.json",
        "Bot_data_base/data/registry.json",
        "Bot_data_base/config.yaml",
    ):
        _write(tmp_path / rel, "{}")

    monkeypatch.setattr(
        runner,
        "_endpoint_matrix_probe",
        lambda **_: {
            "endpoint_matrix_probe": "passed",
            "botdb_query_status": 200,
        },
    )
    monkeypatch.setattr(
        runner,
        "_run_warmup",
        lambda **_: {"warmup_adaptive_status": 200, "botdb_query_status_code": 200},
    )
    fake_case = {
        "case_id": "actual_live_1",
        "http_status": 200,
        "elapsed_ms": 1000,
        "answer_received": True,
        "answer_length": 10,
        "trace_received": True,
        "diagnostic_center_active_for_creator": True,
        "runtime_mode_effective": "creator_only",
        "force_disabled": False,
        "hard_stop_active": False,
        "diagnostic_card_present": True,
        "suggested_writer_move": "give_concrete_example",
        "request_type": "example_request",
        "writer_move_present": True,
        "rag_safe_summary_present": True,
        "writer_chunk_non_empty_preview_count": 1,
        "body_action_offered": False,
        "case_passed": True,
        "fail_reasons": [],
        "timeout_attempts": [{"timeout_sec": 15, "http_status": 200, "elapsed_ms": 1000}],
        "selected_success_timeout_sec": 15,
        "trace_poll_attempts": 0,
        "trace_latency_after_timeout_sec": 0,
        "payload_variant_attempts": [],
        "adaptive_error": None,
        "timeout_classification": "adaptive_completed_but_trace_timeout",
        "session_id_hash": "sha256:x",
        "turn_id_hash": "sha256:y",
    }
    monkeypatch.setattr(
        runner,
        "_run_case_with_timeout_ladder",
        lambda **_: (dict(fake_case), {"classification": "provider_latency", "attempts": [], "payload_variant_attempts": []}, 1),
    )
    monkeypatch.setattr(
        runner,
        "_run_rollback_hard_stop_live",
        lambda **_: {"rollback_hard_stop_live_gate": "passed_with_warning"},
    )
    monkeypatch.setattr(
        runner,
        "_run_normal_user_live_gate",
        lambda **_: ({"normal_user_live_no_effect_gate": "passed"}, 1),
    )
    monkeypatch.setattr(
        runner.encoding_validator,
        "run",
        lambda _args: {"final_status": "passed", "schema_version": "artifact_encoding_hygiene_report_v1"},
    )

    result = runner.run(
        argparse.Namespace(
            repo_root=str(tmp_path),
            reports_dir=str(tmp_path / "TO_DO_LIST" / "reports"),
            output_dir=str(tmp_path / "TO_DO_LIST" / "logs" / "PRD-046.1.37-HF1"),
            backend_base_url="http://localhost:8001",
            botdb_base_url="http://localhost:8003",
            web_ui_base_url="http://localhost:3000",
            api_key="dev-key-001",
            creator_user_id="creator",
            normal_user_id="normal",
            strict=True,
        )
    )
    assert result["status"] in {"passed", "blocked"}
    out_dir = tmp_path / "TO_DO_LIST" / "logs" / "PRD-046.1.37-HF1"
    for name in (
        "source_gate.json",
        "docs_state_pre_rerun_correction.json",
        "endpoint_matrix_probe.json",
        "adaptive_timeout_diagnosis.json",
        "live_latency_profile.json",
        "actual_live_creator_smoke_hf1.json",
        "trace_acceptance_hf1.json",
        "rollback_hard_stop_live_proof.json",
        "normal_user_live_no_effect_gate.json",
        "rag_behavior_regression_gate.json",
        "provider_budget_hf1.json",
        "no_mutation_proof.json",
        "artifact_encoding_hygiene_report.json",
        "prd_046_1_37_hf1_scorecard.json",
    ):
        assert (out_dir / name).exists(), name
