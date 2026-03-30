"""
Tests for shared embedding model reuse between SemanticMemory instances.
"""

from __future__ import annotations

from bot_agent.semantic_memory import SemanticMemory


def test_semantic_memory_uses_shared_model_without_reload(monkeypatch):
    shared_model = object()
    monkeypatch.setattr(SemanticMemory, "_shared_model", shared_model, raising=False)
    monkeypatch.setattr(SemanticMemory, "_shared_model_loaded", True, raising=False)

    called = {"count": 0}

    def _fake_load(self):
        called["count"] += 1

    monkeypatch.setattr(SemanticMemory, "_load_model", _fake_load, raising=False)

    mem_a = SemanticMemory(user_id="u-a")
    mem_b = SemanticMemory(user_id="u-b")

    assert mem_a.model is shared_model
    assert mem_b.model is shared_model
    assert called["count"] == 0
