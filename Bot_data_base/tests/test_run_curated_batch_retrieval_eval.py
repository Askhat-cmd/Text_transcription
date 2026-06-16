from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

import tools.run_curated_batch_retrieval_eval as runner


def _workspace_tmp() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / ".tmp_pytest_prd_047_20"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"runner_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fake_request_json(method: str, url: str, payload=None, timeout: float = 8.0) -> dict:
    del payload, timeout
    if method == "GET" and url.endswith("/api/status"):
        return {"ok": True, "status_code": 200, "body": {"status": "ok"}, "error": ""}
    if method == "GET" and url.endswith("/api/registry"):
        return {"ok": True, "status_code": 200, "body": {"total": 1}, "error": ""}
    if method == "POST" and url.endswith("/api/query/"):
        return {"ok": True, "status_code": 200, "body": {"chunks": []}, "error": ""}
    raise AssertionError(f"Unexpected request: {method} {url}")


def _fake_encoding_validator(_args) -> dict:
    return {
        "prd_id": "PRD-047.20",
        "final_status": "passed",
        "replacement_char_warning_count": 0,
        "files_checked": 0,
    }


def test_select_mode_creates_selection_artifacts() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            mode="select",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed"
    assert (tmp_path / "batch_1_selection.json").exists()
    assert (tmp_path / "batch_1_selection.md").exists()


def test_preflight_mode_creates_eval_only_blocker_reports() -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    result = runner.run(
        argparse.Namespace(
            mode="preflight",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] == "passed_with_expected_blockers"
    payload = json.loads((tmp_path / "batch_1_apply_preflight_report.json").read_text(encoding="utf-8"))
    assert payload["ready_for_live_apply"] is False
    assert payload["ready_for_eval_over_real_overlay"] is True
    assert "human_final_approval_missing" in payload["expected_blockers"]
    assert "evaluation_only_overlay" in payload["expected_blockers"]


def test_eval_mode_creates_dataset_and_results(monkeypatch) -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(runner, "_request_json", _fake_request_json)
    result = runner.run(
        argparse.Namespace(
            mode="eval",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] in {"passed", "warning"}
    assert (tmp_path / "retrieval_eval_dataset.json").exists()
    assert (tmp_path / "retrieval_eval_results.json").exists()
    results = json.loads((tmp_path / "retrieval_eval_results.json").read_text(encoding="utf-8"))
    assert results["schema_version"] == "mechanism_metadata_curated_batch_retrieval_eval_results_v1"
    assert results["cases_total"] == 18


def test_full_mode_creates_required_artifacts(monkeypatch) -> None:
    tmp_path = _workspace_tmp()
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(runner, "_request_json", _fake_request_json)
    monkeypatch.setattr(runner, "load_shared_encoding_validator", lambda: _fake_encoding_validator)
    result = runner.run(
        argparse.Namespace(
            mode="full",
            out_dir=str(tmp_path),
            reports_dir=str(reports_dir),
            botdb_base_url="http://127.0.0.1:8003",
        )
    )
    assert result["status"] in {"passed", "warning"}
    required = [
        "source_gate_report.json",
        "source_gate_report.md",
        "batch_1_selection.json",
        "batch_1_selection.md",
        "batch_1_decisions_pack.json",
        "batch_1_decisions_pack.md",
        "batch_1_accepted_overlay_preview.json",
        "batch_1_accepted_overlay_preview.md",
        "batch_1_apply_preflight_report.json",
        "batch_1_apply_preflight_report.md",
        "batch_1_dry_run_apply_plan.json",
        "batch_1_dry_run_apply_plan.md",
        "retrieval_eval_dataset.json",
        "retrieval_eval_dataset.md",
        "retrieval_eval_results.json",
        "retrieval_eval_results.md",
        "baseline_retrieval_results.json",
        "botdb_readonly_smoke.json",
        "anti_runtime_activation_report.json",
        "no_mutation_proof.json",
        "encoding_hygiene_report.json",
        "implementation_summary.json",
    ]
    for relative in required:
        assert (tmp_path / relative).exists(), relative
    assert (reports_dir / "PRD-047.20_IMPLEMENTATION_REPORT.md").exists()
    assert (reports_dir / "PRD-047.20_NEXT_PRD_RECOMMENDATION.md").exists()
