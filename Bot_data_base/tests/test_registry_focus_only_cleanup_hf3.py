from __future__ import annotations

from tools import run_registry_focus_only_cleanup_hf3 as hf3


def test_registry_focus_only_cleanup_classification():
    rows = [
        {"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247, "title": "Кузница Духа"},
        {"source_id": "avtor__книга", "status": "failed", "blocks_count": 1, "title": "Книга", "author": "Автор"},
        {"source_id": "other_prod", "status": "done", "blocks_count": 3, "title": "Real"},
    ]
    audit, plan, delete_ids = hf3.classify_focus_only_cleanup(
        rows=rows,
        expected_source_id="123__кузница_духа",
        all_blocks_ids={"123__кузница_духа", "other_prod"},
        chroma_count_by_source={"123__кузница_духа": 247, "avtor__книга": 0, "other_prod": 1},
    )
    assert audit["summary"]["keep_count"] == 1
    assert "avtor__книга" in delete_ids
    assert "other_prod" in plan["blocked_source_ids"]
