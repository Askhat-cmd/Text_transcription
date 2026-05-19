from __future__ import annotations

from tools import run_registry_zero_block_cleanup_hf2 as cleanup_tool


def test_zero_block_hygiene_audit_classifies_safe_candidates():
    rows = [
        {"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247},
        {"source_id": "test123", "status": "archived", "blocks_count": 0},
        {"source_id": "book_source", "status": "processing", "blocks_count": 0},
    ]
    audit, plan, safe_ids = cleanup_tool.build_hygiene_audit_and_plan(
        registry_rows=rows,
        expected_source_id="123__кузница_духа",
        all_blocks_source_ids={"123__кузница_духа"},
        chroma_count_by_source={"123__кузница_духа": 247, "test123": 0, "tmp_source": 0},
    )
    assert audit["summary"]["safe_delete_candidates_count"] == 1
    assert "test123" in safe_ids
    assert "book_source" in plan["blocked_delete_source_ids"]
