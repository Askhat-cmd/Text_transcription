from __future__ import annotations

from types import SimpleNamespace

from api.routes import registry


def test_low_block_non_focus_delete_allowed_with_proof(monkeypatch):
    monkeypatch.setattr(registry, "_safe_chroma_source_exists", lambda runner, source_id: (False, "health_source_absent"))
    policy = registry._resolve_delete_policy(
        {
            "source_id": "avtor__книга",
            "source_type": "book",
            "title": "Книга",
            "author": "Автор",
            "status": "failed",
            "blocks_count": 1,
        },
        production_source_ids={"123__кузница_духа"},
        runner=SimpleNamespace(),
    )
    assert policy["allowed"] is True
    assert policy["code"] == "registry_only_blocks_test_like"
