from __future__ import annotations

from pathlib import Path

from tools.controlled_candidate_apply import build_registry_update


def test_registry_focus_row_updated_with_apply_marker(tmp_path: Path) -> None:
    source_export = tmp_path / "books" / "123__кузница_духа_blocks.json"
    registry = [
        {
            "source_id": "123__кузница_духа",
            "source_type": "book",
            "title": "Кузница Духа",
            "status": "done",
            "blocks_count": 229,
            "pipeline_version": "bot_data_base_v1.0",
            "file_paths": {"upload": "data/uploads/books/book.md", "json": "old.json"},
        },
        {"source_id": "test", "status": "archived", "blocks_count": 0, "file_paths": {}},
    ]
    updated, info = build_registry_update(
        registry_records=registry,
        source_id="123__кузница_духа",
        source_export_path=source_export,
        candidate_blocks_count=247,
        source_prd="PRD-046.0.8.1",
    )
    row = updated[info["updated_index"]]
    assert row["blocks_count"] == 247
    assert row["status"] == "done"
    assert row["file_paths"]["json"] == str(source_export)
    assert "candidate_apply_PRD-046.0.8.1" in row["pipeline_version"]
