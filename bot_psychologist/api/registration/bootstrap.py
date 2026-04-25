"""Database bootstrap for registration and API keys."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from api.identity import IdentityService

from .repository import RegistrationRepository
from .security import generate_access_key, hash_key


logger = logging.getLogger(__name__)


class DatabaseBootstrap:
    """Создает schema и seed-данные в идемпотентном режиме."""

    def __init__(
        self,
        *,
        repository: RegistrationRepository,
        identity_service: IdentityService,
    ) -> None:
        self._repository = repository
        self._identity_service = identity_service

    async def run(self) -> None:
        self._repository.ensure_schema()
        seeded_keys = await self._seed_api_keys()
        seeded_admin = await self._seed_admin_user()
        logger.info(
            "database bootstrap complete (tables=5, api_keys_seeded=%s, admin_seeded=%s)",
            seeded_keys,
            seeded_admin,
        )

    async def _seed_api_keys(self) -> int:
        dev_key = (os.getenv("DEV_API_KEY") or "dev-key-001").strip()
        test_key = (os.getenv("TEST_API_KEY") or "test-key-001").strip()
        internal_key = (os.getenv("INTERNAL_TELEGRAM_KEY") or "internal-telegram-key").strip()

        seeded = 0
        if dev_key:
            self._repository.upsert_api_key(
                key_value=dev_key,
                name="Development",
                role="dev",
                rate_limit=1000,
                active=True,
            )
            seeded += 1
        if test_key:
            self._repository.upsert_api_key(
                key_value=test_key,
                name="Test Client",
                role="test",
                rate_limit=100,
                active=True,
            )
            seeded += 1
        if internal_key:
            self._repository.upsert_api_key(
                key_value=internal_key,
                name="Internal Telegram",
                role="internal",
                rate_limit=1000,
                active=True,
            )
            seeded += 1
        return seeded

    async def _seed_admin_user(self) -> bool:
        if self._repository.count_user_profiles() > 0:
            return False

        admin_username = (os.getenv("ADMIN_USERNAME") or "").strip().lower()
        admin_invite_key = (os.getenv("ADMIN_INVITE_KEY") or "").strip()
        if not admin_username or not admin_invite_key:
            return False

        admin_access_key = (os.getenv("ADMIN_ACCESS_KEY") or "").strip() or generate_access_key("BP-ADMIN")
        identity = await self._identity_service.resolve_or_create(
            provider="api",
            external_id=f"registered:{admin_username}",
            session_id=f"bootstrap_admin_{admin_username}",
            channel="api",
            metadata={"source": "bootstrap"},
        )

        self._repository.create_invite_key(
            key_value=admin_invite_key,
            role_grant="admin",
            expires_at=datetime(2999, 1, 1, tzinfo=timezone.utc),
            created_by=identity.user_id,
        )
        self._repository.create_user_profile(
            user_id=identity.user_id,
            username=admin_username,
            hashed_access_key=hash_key(admin_access_key),
            role="admin",
        )
        self._repository.consume_invite_key(admin_invite_key, identity.user_id)

        logger.info("database bootstrap seeded admin user: %s", admin_username)
        return True
