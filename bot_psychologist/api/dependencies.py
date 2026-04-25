# api/dependencies.py
"""
FastAPI dependency providers for preloaded components.

Components are warmed during lifespan startup and reused across requests.
If warmup failed or not enabled, dependencies fall back to lazy init.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request

from bot_agent.config import config
from bot_agent.data_loader import DataLoader, data_loader as _default_data_loader
from bot_agent.graph_client import KnowledgeGraphClient, graph_client as _default_graph_client
from bot_agent.retriever import SimpleRetriever, get_retriever as _get_default_retriever
from .identity import (
    IdentityContext,
    IdentityRepository,
    IdentityService,
    build_fingerprint_from_request,
    extract_legacy_user_id_from_request,
    generate_session_id,
)

_data_loader: Optional[DataLoader] = None
_graph_client: Optional[KnowledgeGraphClient] = None
_retriever: Optional[SimpleRetriever] = None
_embedding_model_warmed: bool = False
_identity_repository: Optional[IdentityRepository] = None
_identity_service: Optional[IdentityService] = None


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


def get_identity_service() -> IdentityService:
    """FastAPI dependency: singleton identity service."""
    global _identity_repository, _identity_service
    if _identity_service is None:
        _identity_repository = IdentityRepository(str(config.BOT_DB_PATH))
        _identity_service = IdentityService(_identity_repository)
    return _identity_service


async def get_identity_context(
    request: Request,
    identity_service: IdentityService = Depends(get_identity_service),
) -> IdentityContext:
    """FastAPI dependency: resolve stable identity context for request."""
    session_id_header = (request.headers.get("X-Session-Id") or "").strip()
    fingerprint_header = (request.headers.get("X-Device-Fingerprint") or "").strip()
    legacy_user_id = await extract_legacy_user_id_from_request(request)

    fingerprint = fingerprint_header or build_fingerprint_from_request(request)
    session_id = session_id_header or generate_session_id()

    try:
        if session_id_header:
            restored = await identity_service.resolve_by_session(session_id_header)
            if restored is not None and not legacy_user_id:
                return restored

        return await identity_service.resolve_or_create(
            provider="web",
            external_id=fingerprint,
            session_id=session_id,
            channel="web",
            metadata={
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
            legacy_user_id=legacy_user_id,
        )
    except Exception:
        fallback_user = legacy_user_id or f"anon-{fingerprint.replace('sha256:', '')[:16]}"
        return IdentityContext(
            user_id=fallback_user,
            session_id=session_id,
            conversation_id=session_id,
            channel="web",
            is_anonymous=True,
            created_new_user=False,
            provider="web",
            external_id=fingerprint,
        )

