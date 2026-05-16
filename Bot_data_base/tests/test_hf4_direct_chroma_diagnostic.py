from __future__ import annotations

from pathlib import Path

from tools import diagnose_chroma_runtime_count as diag


def test_direct_chroma_diagnostic_ok(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        diag,
        "_diagnose_via_chromadb",
        lambda **_: {
            "status": "ok",
            "collection_name": "bot_knowledge_base",
            "persist_directory": str(tmp_path / "db"),
            "total_count": 247,
            "source_ids": ["123__кузница_духа"],
            "count_by_source_id": {"123__кузница_духа": 247},
            "sample_ids_count": 10,
            "sample_ids": ["x"],
            "raw_text_leak_detected": False,
            "errors": [],
            "warnings": [],
        },
    )
    payload = diag.run_diagnostic(
        source_prd="PRD-046.0.7.2-HF4",
        botdb_dir=tmp_path,
        config_path=tmp_path / "config.yaml",
    )
    assert payload["schema_version"] == "direct_chroma_diagnostic_v1"
    assert payload["status"] == "ok"
    assert payload["total_count"] == 247
    assert payload["raw_text_leak_detected"] is False


def test_direct_chroma_diagnostic_unavailable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        diag,
        "_diagnose_via_chromadb",
        lambda **_: {
            "status": "diagnostic_unavailable",
            "collection_name": "bot_knowledge_base",
            "persist_directory": str(tmp_path / "db"),
            "total_count": None,
            "source_ids": [],
            "count_by_source_id": {},
            "sample_ids_count": 0,
            "sample_ids": [],
            "raw_text_leak_detected": False,
            "errors": ["chromadb_import_error:x"],
            "warnings": [],
        },
    )
    payload = diag.run_diagnostic(
        source_prd="PRD-046.0.7.2-HF4",
        botdb_dir=tmp_path,
        config_path=tmp_path / "config.yaml",
    )
    assert payload["status"] == "diagnostic_unavailable"
    assert payload["total_count"] is None
    assert payload["errors"]
