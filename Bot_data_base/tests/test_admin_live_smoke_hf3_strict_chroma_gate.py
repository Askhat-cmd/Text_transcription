from __future__ import annotations

import argparse
from pathlib import Path

from tools import run_admin_live_smoke_hf3


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        source_prd="PRD-046.0.7.2-HF3",
        admin_base_url="http://127.0.0.1:8003",
        require_admin_api=True,
        try_start_server=False,
        startup_timeout_sec=30,
        http_timeout_sec=5.0,
        source_id="123__кузница_духа",
        expected_blocks=247,
        blocks=str(tmp_path / "blocks.json"),
        registry=str(tmp_path / "registry.json"),
        apply_result=str(tmp_path / "apply.json"),
        overlay=str(tmp_path / "overlay.json"),
        review_queue=str(tmp_path / "queue.json"),
        out_dir=str(tmp_path / "out"),
        reports_dir=str(tmp_path / "reports"),
    )


def _smoke(chroma_count: int) -> dict:
    dashboard_body = {
        "blocks": {"production_total": 247, "active_source_blocks": 247, "registry_total": 247},
        "chroma": {"status": "ok", "count": chroma_count, "indexed_source_ids": ["123__кузница_духа"]},
    }
    return {
        "admin_base_url": "http://127.0.0.1:8003",
        "server_launch_mode": "external_existing",
        "admin_runtime_status": "passed",
        "admin_consistency_passed": True,
        "focus_source_id": "123__кузница_духа",
        "focus_blocks_count": 247,
        "dashboard_blocks_count": 247,
        "chroma_count": chroma_count,
        "issues": [],
        "warnings": [],
        "api_checks": {
            "/api/status": {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None},
            "/api/registry": {
                "ok": True,
                "status_code": 200,
                "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
                "error": None,
            },
            "/api/registry/": {
                "ok": True,
                "status_code": 200,
                "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
                "error": None,
            },
            "/api/dashboard": {"ok": True, "status_code": 200, "body": dashboard_body, "error": None},
            "/api/dashboard/": {"ok": True, "status_code": 200, "body": dashboard_body, "error": None},
        },
    }


def _patch_common(monkeypatch, smoke: dict) -> None:
    monkeypatch.setattr(run_admin_live_smoke_hf3, "run_admin_live_smoke", lambda **_: {"smoke": smoke, "manifest": {}, "sanitized_server_log_lines": []})
    monkeypatch.setattr(run_admin_live_smoke_hf3, "_load_historical_chroma_count", lambda: (247, "hist.json"))
    monkeypatch.setattr(run_admin_live_smoke_hf3, "sha256_file", lambda _: "hash")
    monkeypatch.setattr(run_admin_live_smoke_hf3, "read_json", lambda _: {})
    monkeypatch.setattr(
        run_admin_live_smoke_hf3,
        "build_data_consistency_gate",
        lambda **_: {"data_consistency_passed": True},
    )
    monkeypatch.setattr(
        run_admin_live_smoke_hf3,
        "build_apply_route_consistency",
        lambda **_: {"apply_route_consistency_passed": True},
    )
    monkeypatch.setattr(
        run_admin_live_smoke_hf3,
        "build_retrieval_quality_smoke",
        lambda **_: {"retrieval_quality_passed": True},
    )
    monkeypatch.setattr(
        run_admin_live_smoke_hf3,
        "build_writer_kb_policy_smoke",
        lambda **_: {"writer_kb_policy_passed": True},
    )
    monkeypatch.setattr(
        run_admin_live_smoke_hf3,
        "build_no_mutation_proof",
        lambda **_: {
            "all_blocks_merged_mutated": False,
            "registry_mutated": False,
            "provider_called": False,
            "chroma_reindex_performed": False,
            "production_apply_performed": False,
        },
    )


def test_hf3_runner_passes_when_live_chroma_is_247(monkeypatch, tmp_path: Path) -> None:
    _patch_common(monkeypatch, _smoke(247))
    monkeypatch.setattr(run_admin_live_smoke_hf3, "_read_direct_chroma_count", lambda: (247, None))

    result = run_admin_live_smoke_hf3.run(_args(tmp_path))
    assert result["status"] == "passed"
    assert result["strict_quality_gate_hf3"]["quality_gate_passed"] is True
    assert result["chroma_count_reconciliation"]["strict_gate_passed"] is True


def test_hf3_runner_blocks_live_229_even_with_historical_247(monkeypatch, tmp_path: Path) -> None:
    _patch_common(monkeypatch, _smoke(229))
    monkeypatch.setattr(run_admin_live_smoke_hf3, "_read_direct_chroma_count", lambda: (247, None))

    result = run_admin_live_smoke_hf3.run(_args(tmp_path))
    assert result["status"] == "done_with_chroma_count_blocker"
    assert result["strict_quality_gate_hf3"]["quality_gate_passed"] is False
    assert result["admin_live_smoke_hf3"]["admin_runtime_status"] == "blocked_chroma_count_mismatch"
    assert "dashboard_chroma_count_mismatch" in result["chroma_count_reconciliation"]["issues"]
