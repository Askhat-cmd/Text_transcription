"""Business logic for identity resolution."""

from __future__ import annotations

import logging
from typing import Optional

from .models import IdentityContext, LinkedIdentity, SessionRecord, UserRecord
from .repository import IdentityRepository

logger = logging.getLogger(__name__)


class IdentityService:
    """Service for canonical identity resolution and linking."""

    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    async def resolve_or_create(
        self,
        *,
        provider: str,
        external_id: str,
        session_id: str,
        channel: str = "web",
        metadata: Optional[dict] = None,
        legacy_user_id: Optional[str] = None,
    ) -> IdentityContext:
        """Resolve canonical user by external identity or create a new user."""
        provider_norm = (provider or "web").strip() or "web"
        external_norm = (external_id or "").strip()
        session_norm = (session_id or "").strip()
        if not external_norm:
            raise ValueError("external_id is required")
        if not session_norm:
            raise ValueError("session_id is required")

        resolved_user: Optional[UserRecord] = None
        resolved_via = provider_norm
        created_new_user = False

        legacy_norm = (legacy_user_id or "").strip()
        if legacy_norm:
            resolved_user = self.repository.find_user_by_identity(
                provider="legacy",
                external_id=legacy_norm,
            )
            if resolved_user is not None:
                resolved_via = "legacy"

        if resolved_user is None:
            resolved_user = self.repository.find_user_by_identity(
                provider=provider_norm,
                external_id=external_norm,
            )

        if resolved_user is None:
            resolved_user = self.repository.create_user(metadata_json=metadata or {})
            created_new_user = True
            linked_identity = self.repository.add_linked_identity(
                user_id=resolved_user.id,
                provider=provider_norm,
                external_id=external_norm,
                metadata_json=metadata or {},
            )
            if linked_identity.user_id != resolved_user.id:
                logger.warning(
                    "identity.fingerprint_collision",
                    extra={
                        "provider": provider_norm,
                        "fingerprint_prefix": external_norm[:16],
                        "existing_user_id": linked_identity.user_id,
                        "attempted_user_id": resolved_user.id,
                    },
                )
                existing_user = self.repository.get_user(linked_identity.user_id)
                if existing_user is not None:
                    resolved_user = existing_user
                    created_new_user = False
            logger.info(
                "identity.user_created",
                extra={"user_id": resolved_user.id, "provider": provider_norm},
            )
        else:
            self.repository.add_linked_identity(
                user_id=resolved_user.id,
                provider=provider_norm,
                external_id=external_norm,
                metadata_json=metadata or {},
            )
            logger.info(
                "identity.user_resolved",
                extra={"user_id": resolved_user.id, "provider": provider_norm},
            )

        if legacy_norm:
            self.repository.add_linked_identity(
                user_id=resolved_user.id,
                provider="legacy",
                external_id=legacy_norm,
                metadata_json={"source": "request_body"},
            )
            logger.warning(
                "identity.legacy_user_id_used",
                extra={
                    "legacy_id": legacy_norm,
                    "user_id": resolved_user.id,
                    "fingerprint_prefix": external_norm[:16],
                },
            )

        self.repository.upsert_session(
            session_id=session_norm,
            user_id=resolved_user.id,
            channel=channel,
            device_fingerprint=external_norm,
            metadata_json=metadata or {},
        )
        logger.info(
            "identity.session_refreshed",
            extra={"session_id": session_norm, "user_id": resolved_user.id},
        )

        return IdentityContext(
            user_id=resolved_user.id,
            session_id=session_norm,
            conversation_id=session_norm,
            channel=channel,  # type: ignore[arg-type]
            is_anonymous=not bool(legacy_norm),
            created_new_user=created_new_user,
            provider=resolved_via,  # type: ignore[arg-type]
            external_id=external_norm,
        )

    async def resolve_by_session(self, session_id: str) -> Optional[IdentityContext]:
        """Restore identity context from known session id."""
        record = self.repository.get_session(session_id)
        if record is None or not record.user_id:
            return None
        self.repository.update_session_last_seen(session_id)
        return IdentityContext(
            user_id=record.user_id,
            session_id=record.session_id,
            conversation_id=record.session_id,
            channel=record.channel,  # type: ignore[arg-type]
            is_anonymous=False,
            created_new_user=False,
            provider="web",
            external_id=record.device_fingerprint,
        )

    async def resolve_telegram(self, telegram_user_id: str) -> Optional[IdentityContext]:
        """Resolve identity by telegram user id if link already exists."""
        telegram_norm = (telegram_user_id or "").strip()
        if not telegram_norm:
            return None
        user = self.repository.find_user_by_identity(provider="telegram", external_id=telegram_norm)
        if user is None:
            return None
        sessions = self.repository.list_active_sessions(user.id, limit=1)
        if sessions:
            session = sessions[0]
            session_id = session.session_id
        else:
            session = self.repository.upsert_session(
                session_id=f"telegram_{telegram_norm}",
                user_id=user.id,
                channel="telegram",
                device_fingerprint=f"telegram:{telegram_norm}",
            )
            session_id = session.session_id
        return IdentityContext(
            user_id=user.id,
            session_id=session_id,
            conversation_id=session_id,
            channel="telegram",
            is_anonymous=False,
            created_new_user=False,
            provider="telegram",
            external_id=telegram_norm,
        )

    async def link_identity(
        self,
        *,
        user_id: str,
        provider: str,
        external_id: str,
        metadata: Optional[dict] = None,
    ) -> LinkedIdentity:
        """Link additional provider identity to canonical user."""
        return self.repository.add_linked_identity(
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            metadata_json=metadata or {},
        )

    async def get_user(self, user_id: str) -> Optional[UserRecord]:
        return self.repository.get_user(user_id)

    async def get_linked_identities(self, user_id: str) -> list[LinkedIdentity]:
        return self.repository.get_linked_identities(user_id)

    async def get_active_sessions(self, user_id: str, limit: int = 20) -> list[SessionRecord]:
        return self.repository.list_active_sessions(user_id, limit=limit)
