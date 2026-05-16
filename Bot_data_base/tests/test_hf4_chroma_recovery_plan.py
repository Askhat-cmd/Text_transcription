from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools import run_chroma_recovery_hf4 as hf4


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        source_prd="PRD-046.0.7.2-HF4",
        admin_base_url="http://127.0.0.1:8003",
        expected_source_id="123__кузница_духа",
        expected_blocks=247,
        config_path=str(tmp_path / "config.yaml"),
        blocks_path=str(tmp_path / "all_blocks_merged.json"),
        registry_path=str(tmp_path / "registry.json"),
        backup_root=str(tmp_path / "backups"),
        out_dir=str(tmp_path / "out"),
        reports_dir=str(tmp_path / "reports"),
    )


def _smoke(chroma_count: int, status: str = "passed") -> dict:
    body_dash = {
        "blocks": {"production_total": 247, "active_source_blocks": 247, "registry_total": 247},
        "chroma": {"status": "ok", "count": chroma_count, "indexed_source_ids": ["123__кузница_духа"]},
    }
    return {
        "admin_runtime_status": status,
        "admin_consistency_passed": status == "passed",
        "dashboard_blocks_count": 247,
        "chroma_count": chroma_count,
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
            "/api/dashboard": {"ok": True, "status_code": 200, "body": body_dash, "error": None},
            "/api/dashboard/": {"ok": True, "status_code": 200, "body": body_dash, "error": None},
        },
    }


def test_hf4_route_controlled_reindex_when_live_and_direct_mismatch(monkeypatch, tmp_path: Path) -> None:
    _write_json(
        tmp_path / "all_blocks_merged.json",
        {"blocks": [{"id": "b1", "source": "book:123__кузница_духа", "text": "x", "metadata": {"source_id": "123__кузница_духа", "governance": {"allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]}}}] * 247},
    )
    _write_json(
        tmp_path / "registry.json",
        [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}],
    )
    _write_json(tmp_path / "config.yaml", {"storage": {"chroma_db_path": "data/chroma_db", "collection_name": "bot_knowledge_base"}})

    monkeypatch.setattr(
        hf4,
        "build_source_hygiene_live_preflight",
        lambda **_: {
            "issues": [],
            "warnings": [],
            "source_hygiene_focus_only": True,
            "focus_blocks": 247,
        },
    )

    diags = iter(
        [
            {"status": "ok", "total_count": 229, "source_ids": ["123__кузница_духа"], "errors": [], "warnings": []},
            {"status": "ok", "total_count": 247, "source_ids": ["123__кузница_духа"], "errors": [], "warnings": []},
        ]
    )
    monkeypatch.setattr(hf4, "run_diagnostic", lambda **_: next(diags))

    smokes = iter([_smoke(229, "blocked_chroma_count_mismatch"), _smoke(247, "passed")])
    monkeypatch.setattr(hf4, "run_admin_live_smoke", lambda **_: {"smoke": next(smokes)})

    monkeypatch.setattr(
        hf4,
        "run_controlled_reindex",
        lambda **_: {
            "result": {"status": "passed", "reindex_performed": True, "chroma_count_after": 247},
            "backup_manifest": {"copied": True, "errors": []},
        },
    )
    monkeypatch.setattr(hf4, "build_data_consistency_gate", lambda **_: {"data_consistency_passed": True})
    monkeypatch.setattr(hf4, "build_retrieval_quality_smoke", lambda **_: {"retrieval_quality_passed": True})
    monkeypatch.setattr(hf4, "build_writer_kb_policy_smoke", lambda **_: {"writer_kb_policy_passed": True})

    result = hf4.run(_args(tmp_path))
    assert result["status"] == "passed"
    assert result["chroma_recovery_plan"]["route"] == "controlled_reindex_focus_source"
    assert result["strict_quality_gate_hf4"]["strict_chroma_count_passed"] is True
