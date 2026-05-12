from __future__ import annotations

from pathlib import Path

from tools.clean_source_reprocess import run_clean_reprocess_candidate


def test_candidate_schema_and_source_id_preserved(tmp_path: Path) -> None:
    raw = tmp_path / "book.md"
    raw.write_text(
        "# Практика\n"
        "Цель: снизить напряжение\n"
        "Время: 5 минут\n"
        "Шаг 1. Дыши медленно\n"
        "Шаг 2. Запиши наблюдения\n",
        encoding="utf-8",
    )
    preflight = {
        "passed": True,
        "raw_markdown_path": str(raw),
        "active_source_id": "123__кузница_духа",
        "active_source_title": "Кузница Духа",
        "active_source_type": "book",
        "_registry_row": {
            "author": "Автор",
            "author_id": "123",
            "language": "ru",
        },
    }
    payload = run_clean_reprocess_candidate(
        source_prd="PRD-046.0.8",
        preflight=preflight,
        config={"chunking": {"book": {"target_tokens": 50, "min_tokens": 10, "max_tokens": 200, "overlap_tokens": 0}}},
    )
    assert payload["schema_version"] == "clean_reprocess_candidate_v1"
    assert payload["processing"]["sd_labeling_active"] is False
    assert payload["candidate"]["blocks_count"] > 0
    for block in payload["candidate"]["blocks"]:
        assert block["source"].endswith("123__кузница_духа")
        governance = (block.get("metadata") or {}).get("governance") or {}
        assert governance.get("chunk_type")
