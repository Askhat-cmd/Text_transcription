from __future__ import annotations

from tools import run_live_botdb_chroma_registry_audit_hf1 as runner


def test_zero_block_hygiene_classification_protects_focus_source():
    rows = [
        {"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247},
        {"source_id": "test123", "status": "failed", "blocks_count": 0},
        {"source_id": "archived_x", "status": "archived", "blocks_count": 0},
        {"source_id": "unsafe", "status": "done", "blocks_count": 5},
    ]

    audit, plan = runner._classify_zero_block_hygiene(rows, "123__кузница_духа")

    assert "123__кузница_духа" in audit["focus_source_protected"]
    assert "unsafe" in audit["unsafe_delete_candidates"]
    assert plan["cleanup_performed"] is False
    assert "unsafe" in plan["blocked_delete_candidates"]
