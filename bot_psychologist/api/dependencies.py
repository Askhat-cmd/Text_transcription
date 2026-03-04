# api/dependencies.py
"""
FastAPI dependency providers for preloaded components.

Components are warmed during lifespan startup and reused across requests.
If warmup failed or not enabled, dependencies fall back to lazy init.
"""
from __future__ import annotations

from typing import Optional

from bot_agent.data_loader import DataLoader, data_loader as _default_data_loader
from bot_agent.graph_client import KnowledgeGraphClient, graph_client as _default_graph_client
from bot_agent.retriever import SimpleRetriever, get_retriever as _get_default_retriever

_data_loader: Optional[DataLoader] = None
_graph_client: Optional[KnowledgeGraphClient] = None
_retriever: Optional[SimpleRetriever] = None
_embedding_model_warmed: bool = False


def set_preloaded_components(
    data_loader: DataLoader,
    graph_client: KnowledgeGraphClient,
    retriever: SimpleRetriever,
) -> None:
    """Register preloaded components from lifespan warmup."""
    global _data_loader, _graph_client, _retriever, _embedding_model_warmed
    _data_loader = data_loader
    _graph_client = graph_client
    _retriever = retriever
    _embedding_model_warmed = True


def get_data_loader() -> DataLoader:
    """FastAPI dependency: return preloaded DataLoader or lazy singleton."""
    return _data_loader or _default_data_loader


def get_graph_client() -> KnowledgeGraphClient:
    """FastAPI dependency: return preloaded GraphClient or lazy singleton."""
    return _graph_client or _default_graph_client


def get_retriever() -> SimpleRetriever:
    """FastAPI dependency: return preloaded Retriever or lazy singleton."""
    return _retriever or _get_default_retriever()


def is_embedding_model_warm() -> bool:
    """Whether semantic embedding model was warmed during startup."""
    return _embedding_model_warmed

