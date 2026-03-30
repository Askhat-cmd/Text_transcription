"""
Tests for Knowledge Graph toggle (PRD v0.6.0 Block 5).
"""

from __future__ import annotations

from bot_agent.config import config
from bot_agent.graph_client import KnowledgeGraphClient


def test_graph_client_disabled_by_default(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_KNOWLEDGE_GRAPH", False, raising=False)
    client = KnowledgeGraphClient()

    client.load_graphs_from_all_documents()

    assert client.has_data() is False
    assert client._is_loaded is True


def test_graph_client_enabled_can_load_empty_dataset(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_KNOWLEDGE_GRAPH", True, raising=False)
    import bot_agent.graph_client as graph_module

    monkeypatch.setattr(graph_module.data_loader, "get_all_documents", lambda: [], raising=False)
    client = KnowledgeGraphClient()
    client.load_graphs_from_all_documents()

    assert client._is_loaded is True
    assert client.has_data() is False
