# api/dependencies.py
"""
FastAPI dependency providers for preloaded components.

Components are warmed during lifespan startup and reused across requests.
If warmup failed or not enabled, dependencies fall back to lazy init.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from bot_agent.config import config
from bot_agent.data_loader import DataLoader, data_loader as _default_data_loader
from bot_agent.graph_client import KnowledgeGraphClient, graph_client as _default_graph_client
from bot_agent.retriever import SimpleRetriever, get_retriever as _get_default_retriever

from .conversations import ConversationRepository, ConversationService
from .identity import (
    IdentityContext,
    IdentityRepository,
    IdentityService,
    build_fingerprint_from_request,
    extract_legacy_user_id_from_request,
    generate_session_id,
    hash_ip,
    resolve_client_ip,
)
from .registration import DatabaseBootstrap, LinkAttemptGuard, RegistrationRepository, RegistrationService
from .registration.models import SessionContext
from .telegram_adapter.config import telegram_settings
from .telegram_adapter.outbound import TelegramOutboundSender
from .telegram_adapter.service import TelegramAdapterService

_data_loader: Optional[DataLoader] = None
_graph_client: Optional[KnowledgeGraphClient] = None
_retriever: Optional[SimpleRetriever] = None
_embedding_model_warmed: bool = False
_identity_repository: Optional[IdentityRepository] = None
_identity_service: Optional[IdentityService] = None
_conversation_repository: Optional[ConversationRepository] = None
_conversation_service: Optional[ConversationService] = None
_registration_repository: Optional[RegistrationRepository] = None
_link_attempt_guard: Optional[LinkAttemptGuard] = None
_registration_service: Optional[RegistrationService] = None
_database_bootstrap: Optional[DatabaseBootstrap] = None
_telegram_outbound_sender: Optional[TelegramOutboundSender] = None
_telegram_adapter_service: Optional[TelegramAdapterService] = None

logger = logging.getLogger(__name__)


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


def get_conversation_service() -> ConversationService:
    """FastAPI dependency: singleton conversation service."""
    global _conversation_repository, _conversation_service
    if _conversation_service is None:
        _conversation_repository = ConversationRepository(str(config.BOT_DB_PATH))
        _conversation_service = ConversationService(_conversation_repository)
    return _conversation_service


def get_registration_repository() -> RegistrationRepository:
    """FastAPI dependency: singleton registration repository."""
    global _registration_repository
    if _registration_repository is None:
        _registration_repository = RegistrationRepository(str(config.BOT_DB_PATH))
    return _registration_repository


def get_link_attempt_guard() -> LinkAttemptGuard:
    """FastAPI dependency: singleton link attempt guard."""
    global _link_attempt_guard
    if _link_attempt_guard is None:
        _link_attempt_guard = LinkAttemptGuard(max_attempts=5, window_seconds=900)
    return _link_attempt_guard


def get_registration_service() -> RegistrationService:
    """FastAPI dependency: singleton registration service."""
    global _registration_service
    if _registration_service is None:
        _registration_service = RegistrationService(
            repository=get_registration_repository(),
            identity_service=get_identity_service(),
            link_guard=get_link_attempt_guard(),
        )
    return _registration_service


def get_database_bootstrap() -> DatabaseBootstrap:
    """FastAPI dependency: singleton bootstrap service."""
    global _database_bootstrap
    if _database_bootstrap is None:
        _database_bootstrap = DatabaseBootstrap(
            repository=get_registration_repository(),
            identity_service=get_identity_service(),
        )
    return _database_bootstrap


def get_telegram_outbound_sender() -> TelegramOutboundSender:
    """FastAPI dependency: singleton outbound sender for telegram."""
    global _telegram_outbound_sender
    if _telegram_outbound_sender is None:
        bot_token = telegram_settings.bot_token
        if not bot_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram bot token is not configured",
            )
        _telegram_outbound_sender = TelegramOutboundSender(bot_token=bot_token)
    return _telegram_outbound_sender


def get_telegram_adapter_service() -> TelegramAdapterService:
    """FastAPI dependency: singleton telegram adapter service."""
    global _telegram_adapter_service
    if _telegram_adapter_service is None:
        _telegram_adapter_service = TelegramAdapterService(
            identity_service=get_identity_service(),
            conversation_service=get_conversation_service(),
            registration_service=get_registration_service(),
        )
    return _telegram_adapter_service


async def get_current_session_context(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> SessionContext:
    """Resolve session context from `Authorization: Bearer <token>`."""
    header = (authorization or "").strip()
    if not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token is required",
        )

    token = header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is required",
        )

    session = await registration_service.resolve_session_context(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is invalid or expired",
        )
    return session


async def get_identity_context(
    request: Request,
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-Id"),
    x_device_fingerprint: Optional[str] = Header(default=None, alias="X-Device-Fingerprint"),
    x_conversation_id: Optional[str] = Header(default=None, alias="X-Conversation-Id"),
    identity_service: IdentityService = Depends(get_identity_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> IdentityContext:
    """FastAPI dependency: resolve stable identity context for request."""
    session_id_header = x_session_id.strip() if isinstance(x_session_id, str) else ""
    fingerprint_header = (
        x_device_fingerprint.strip() if isinstance(x_device_fingerprint, str) else ""
    )
    legacy_user_id = await extract_legacy_user_id_from_request(request)
    conversation_id_header = (
        x_conversation_id.strip() if isinstance(x_conversation_id, str) else ""
    )

    fingerprint = fingerprint_header or build_fingerprint_from_request(request)
    # Для web-кейса без X-Session-Id используем стабильный технический session key,
    # чтобы не пересоздавать conversation на каждом запросе.
    session_id = session_id_header or fingerprint[:32]
    client_ip = resolve_client_ip(request)
    user_agent = (request.headers.get("user-agent") or "").strip()
    metadata = {
        "ip_hash": hash_ip(client_ip),
        "user_agent_prefix": user_agent[:80],
        "channel": "web",
    }

    try:
        identity: Optional[IdentityContext] = None
        if session_id_header:
            restored = await identity_service.resolve_by_session(session_id_header)
            if restored is not None and not legacy_user_id:
                identity = restored

        if identity is None:
            identity = await identity_service.resolve_or_create(
                provider="web",
                external_id=fingerprint,
                session_id=session_id,
                channel="web",
                metadata=metadata,
                legacy_user_id=legacy_user_id,
            )

        resolved_conversation = None
        if conversation_id_header:
            resolved_conversation = await conversation_service.get_conversation_context(
                conversation_id_header
            )
            if (
                resolved_conversation is None
                or resolved_conversation.user_id != identity.user_id
            ):
                resolved_conversation = None

        if resolved_conversation is None:
            resolved_conversation = await conversation_service.get_or_create_conversation(
                user_id=identity.user_id,
                session_id=identity.session_id,
                channel=identity.channel,
            )

        profile = get_registration_repository().get_profile_by_user_id(identity.user_id)
        resolved_role = str(profile.get("role") or identity.role) if profile else identity.role
        resolved_username = str(profile.get("username") or "") if profile else (identity.username or "")
        resolved_is_registered = bool(profile) or identity.is_registered

        return IdentityContext(
            user_id=identity.user_id,
            session_id=identity.session_id,
            conversation_id=resolved_conversation.conversation_id,
            channel=identity.channel,
            is_anonymous=identity.is_anonymous,
            created_new_user=identity.created_new_user,
            provider=identity.provider,
            external_id=identity.external_id,
            role=resolved_role,
            username=resolved_username or None,
            is_registered=resolved_is_registered,
        )
    except Exception as exc:
        logger.error(
            "identity.resolve_failed",
            extra={"error": str(exc), "fingerprint_prefix": fingerprint[:8]},
            exc_info=True,
        )
        fallback_token = uuid.uuid4().hex
        fallback_user = f"anon_{fallback_token}"
        fallback_session = f"fallback_{uuid.uuid4().hex}"
        fallback_conversation = f"fallback_{uuid.uuid4().hex}"
        return IdentityContext(
            user_id=fallback_user,
            session_id=fallback_session,
            conversation_id=fallback_conversation,
            channel="web",
            is_anonymous=True,
            created_new_user=False,
            provider="web",
            external_id=fingerprint,
            role="anonymous",
            username=None,
            is_registered=False,
        )
