from __future__ import annotations

from types import SimpleNamespace

from api.routes import registry


def test_safe_chroma_source_exists_falls_back_to_health(monkeypatch):
    runner = SimpleNamespace(
        chroma_manager=SimpleNamespace(
            source_exists=lambda source_id: (_ for _ in ()).throw(TypeError("object of type 'int' has no len()"))
        )
    )
    monkeypatch.setattr(
        registry,
        "get_chroma_runtime_health",
        lambda config_path: {"status": "ok", "source_ids": ["123__кузница_духа"], "count_by_source_id": {"123__кузница_духа": 247}},
    )
    exists, reason = registry._safe_chroma_source_exists(runner, "avtor__книга")
    assert exists is False
    assert reason in {"health_source_absent", "health_count_by_source_absent"}
