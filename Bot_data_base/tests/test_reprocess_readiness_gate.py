from __future__ import annotations

from pathlib import Path

from tools.reprocess_readiness_gate import build_reprocess_readiness_payload


def test_reprocess_gate_ready_when_single_focus_and_sd_disabled(tmp_path: Path) -> None:
    botdb = tmp_path / "Bot_data_base"
    upload_dir = botdb / "data" / "uploads" / "books"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "КУЗНИЦА ДУХА v.2.md").write_text("focus", encoding="utf-8")

    registry = [
        {
            "source_id": "123__кузница_духа",
            "title": "Кузница Духа",
            "source_type": "book",
            "status": "done",
            "blocks_count": 2,
            "file_paths": {"upload": "data/uploads/books/КУЗНИЦА ДУХА v.2.md"},
        }
    ]
    blocks = [
        {"source": "book:123__кузница_духа", "text": "a", "metadata": {"source_id": "123__кузница_духа"}},
        {"source": "book:123__кузница_духа", "text": "b", "metadata": {"source_id": "123__кузница_духа"}},
    ]
    payload = build_reprocess_readiness_payload(
        source_prd="PRD-046.0.7-HF1",
        registry_records=registry,
        all_blocks=blocks,
        hygiene_audit={"focus_source_candidates": ["123__кузница_духа"], "summary": {"sources_zero_blocks": 0}, "sources": []},
        hygiene_plan={"valid": True},
        legacy_sd_report={"legacy_sd_filter_still_active": False},
        review_queue={"review_items_count": 10},
        botdb_dir=botdb,
    )
    assert payload["ready_for_clean_reprocess"] is True
    assert payload["status"] == "ready"
    assert payload["blockers"] == []


def test_reprocess_gate_not_ready_on_multiple_active_and_sd_filter(tmp_path: Path) -> None:
    botdb = tmp_path / "Bot_data_base"
    (botdb / "data" / "uploads" / "books").mkdir(parents=True, exist_ok=True)

    registry = [
        {
            "source_id": "123__кузница_духа",
            "title": "Кузница Духа",
            "source_type": "book",
            "status": "done",
            "blocks_count": 2,
            "file_paths": {},
        },
        {
            "source_id": "test123",
            "title": "",
            "source_type": "youtube",
            "status": "processing",
            "blocks_count": 0,
            "file_paths": {},
        },
    ]
    blocks = [{"source": "book:123__кузница_духа", "text": "a", "metadata": {"source_id": "123__кузница_духа"}}]
    payload = build_reprocess_readiness_payload(
        source_prd="PRD-046.0.7-HF1",
        registry_records=registry,
        all_blocks=blocks,
        hygiene_audit={"focus_source_candidates": ["123__кузница_духа"], "summary": {"sources_zero_blocks": 1}, "sources": []},
        hygiene_plan={"valid": True},
        legacy_sd_report={"legacy_sd_filter_still_active": True},
        review_queue=None,
        botdb_dir=botdb,
    )
    assert payload["ready_for_clean_reprocess"] is False
    assert payload["status"] == "not_ready"
    assert "multiple_active_sources_without_allowlist" in payload["blockers"]
    assert "legacy_sd_filter_still_active" in payload["blockers"]
