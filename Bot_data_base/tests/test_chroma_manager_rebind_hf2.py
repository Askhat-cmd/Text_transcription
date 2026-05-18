from __future__ import annotations

from storage.chroma_manager import ChromaManager


def test_chroma_manager_get_stats_safe_refresh(monkeypatch):
    monkeypatch.setenv("BOT_DB_DISABLE_EMBEDDINGS", "1")
    manager = ChromaManager(db_path=":memory:", collection_name="abc", embedding_model_name="dummy")

    calls = {"count": 0}

    def fake_get_stats():
        calls["count"] += 1
        if calls["count"] == 1:
            raise TypeError("object of type 'int' has no len()")
        return {"total": 247, "by_sd_level": {"GREEN": 247}, "by_source_type": {"book": 247}}

    monkeypatch.setattr(manager, "get_stats", fake_get_stats)
    monkeypatch.setattr(manager, "refresh_collection_binding", lambda: {"status": "ok", "refreshed": True})

    payload = manager.get_stats_safe(refresh_on_error=True)

    assert payload["status"] == "ok"
    assert payload["total"] == 247
    assert payload["binding_refreshed"] is True
