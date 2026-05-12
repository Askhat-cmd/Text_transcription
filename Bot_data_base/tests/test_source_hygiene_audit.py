from __future__ import annotations

import json
from pathlib import Path

from tools.source_hygiene_audit import build_source_hygiene_audit, run_audit_cli


def test_build_source_hygiene_audit_classifies_focus_and_test_sources(tmp_path: Path) -> None:
    botdb_dir = tmp_path / "Bot_data_base"
    (botdb_dir / "data" / "processed" / "books").mkdir(parents=True, exist_ok=True)
    (botdb_dir / "data" / "uploads" / "books").mkdir(parents=True, exist_ok=True)
    focus_upload = botdb_dir / "data" / "uploads" / "books" / "КУЗНИЦА ДУХА v.2.md"
    focus_upload.write_text("focus", encoding="utf-8")
    focus_export = botdb_dir / "data" / "processed" / "books" / "123__кузница_духа_blocks.json"
    focus_export.write_text("[]", encoding="utf-8")

    registry_records = [
        {
            "source_id": "123__кузница_духа",
            "title": "Кузница Духа",
            "author": "Саламат",
            "source_type": "book",
            "status": "done",
            "blocks_count": 229,
            "file_paths": {
                "upload": "data/uploads/books/КУЗНИЦА ДУХА v.2.md",
                "json": "data/processed/books/123__кузница_духа_blocks.json",
            },
        },
        {
            "source_id": "test123",
            "title": "",
            "author": "Автор",
            "source_type": "youtube",
            "status": "processing",
            "blocks_count": 0,
            "file_paths": {},
        },
    ]
    blocks = [{"source": "book:123__кузница_духа", "text": "x", "metadata": {"source_id": "123__кузница_духа"}}] * 229
    payload = build_source_hygiene_audit(
        registry_records=registry_records,
        processed_blocks=blocks,
        botdb_dir=botdb_dir,
    )
    assert payload["summary"]["total_sources"] == 2
    assert payload["summary"]["processing_stale_sources"] == 1
    assert "123__кузница_духа" in payload["focus_source_candidates"]
    row_by_id = {row["source_id"]: row for row in payload["sources"]}
    assert row_by_id["123__кузница_духа"]["recommended_hygiene_action"] == "keep"
    assert row_by_id["test123"]["recommended_hygiene_action"] == "archive"


def test_run_audit_cli_degraded_when_inputs_missing(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / "Bot_data_base").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(repo_root)

    output_json = repo_root / "out" / "audit.json"
    output_md = repo_root / "out" / "audit.md"
    payload = run_audit_cli(
        output_json=output_json,
        output_md=output_md,
        registry_path=None,
        all_blocks_path=None,
        focus_hint="кузниц",
        source_prd="PRD-046.0.7-HF1",
    )
    assert payload["mode"] == "degraded"
    assert output_json.exists()
    assert output_md.exists()
    dumped = json.loads(output_json.read_text(encoding="utf-8"))
    assert dumped["schema_version"] == "source_hygiene_audit_v1"
