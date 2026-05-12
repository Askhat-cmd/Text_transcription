from __future__ import annotations

from pathlib import Path

from tools.clean_source_reprocess import build_clean_reprocess_preflight


def _base_registry(upload_path: str) -> list[dict]:
    return [
        {
            "source_id": "123__кузница_духа",
            "source_type": "book",
            "title": "Кузница Духа",
            "author": "Автор",
            "author_id": "123",
            "language": "ru",
            "status": "done",
            "blocks_count": 229,
            "file_paths": {"upload": upload_path},
        }
    ]


def test_preflight_fails_when_readiness_not_ready(tmp_path: Path) -> None:
    botdb = tmp_path / "Bot_data_base"
    raw = botdb / "data" / "uploads" / "books" / "book.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("text", encoding="utf-8")

    preflight = build_clean_reprocess_preflight(
        source_prd="PRD-046.0.8",
        readiness_payload={
            "ready_for_clean_reprocess": False,
            "active_source_count": 1,
            "active_source_id": "123__кузница_духа",
            "legacy_sd_active": False,
            "chroma_count": 229,
        },
        registry_records=_base_registry("data/uploads/books/book.md"),
        all_blocks=[{"source": "book:123__кузница_духа", "text": "x", "metadata": {"source_id": "123__кузница_духа"}}],
        botdb_dir=botdb,
        hash_before={},
    )
    assert preflight["passed"] is False
    assert "readiness_gate_not_ready" in preflight["blockers"]


def test_preflight_fails_when_raw_missing(tmp_path: Path) -> None:
    botdb = tmp_path / "Bot_data_base"
    preflight = build_clean_reprocess_preflight(
        source_prd="PRD-046.0.8",
        readiness_payload={
            "ready_for_clean_reprocess": True,
            "active_source_count": 1,
            "active_source_id": "123__кузница_духа",
            "legacy_sd_active": False,
            "chroma_count": 229,
        },
        registry_records=_base_registry("data/uploads/books/missing.md"),
        all_blocks=[{"source": "book:123__кузница_духа", "text": "x", "metadata": {"source_id": "123__кузница_духа"}}],
        botdb_dir=botdb,
        hash_before={},
    )
    assert preflight["passed"] is False
    assert "raw_markdown_missing" in preflight["blockers"]


def test_preflight_passes_for_single_active_source(tmp_path: Path) -> None:
    botdb = tmp_path / "Bot_data_base"
    raw = botdb / "data" / "uploads" / "books" / "book.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("# Глава 1\nТекст\n", encoding="utf-8")

    preflight = build_clean_reprocess_preflight(
        source_prd="PRD-046.0.8",
        readiness_payload={
            "ready_for_clean_reprocess": True,
            "active_source_count": 1,
            "active_source_id": "123__кузница_духа",
            "legacy_sd_active": False,
            "chroma_count": 229,
        },
        registry_records=_base_registry("data/uploads/books/book.md"),
        all_blocks=[{"source": "book:123__кузница_духа", "text": "x", "metadata": {"source_id": "123__кузница_духа"}}],
        botdb_dir=botdb,
        hash_before={},
    )
    assert preflight["passed"] is True
    assert preflight["raw_markdown_found"] is True
    assert preflight["active_source_id"] == "123__кузница_духа"
