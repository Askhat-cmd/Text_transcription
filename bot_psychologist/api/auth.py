# api/auth.py
"""
API Key Authentication & Rate Limiting for Bot Psychologist API.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException, status

from bot_agent.config import config

from .registration import RegistrationRepository


logger = logging.getLogger(__name__)


class APIKeyManager:
    """Управление API ключами через БД + in-memory rate limiting."""

    def __init__(self) -> None:
        self._repository: Optional[RegistrationRepository] = None
        self._last_db_path: Optional[str] = None
        self.request_counts: dict[str, int] = {}

    def _get_repository(self) -> RegistrationRepository:
        db_path = str(config.BOT_DB_PATH)
        if self._repository is None or self._last_db_path != db_path:
            self._repository = RegistrationRepository(db_path)
            self._last_db_path = db_path
        return self._repository

    def _ensure_default_keys(self) -> None:
        repo = self._get_repository()
        dev_key = (os.getenv("DEV_API_KEY") or "dev-key-001").strip()
        test_key = (os.getenv("TEST_API_KEY") or "test-key-001").strip()
        internal_key = (os.getenv("INTERNAL_TELEGRAM_KEY") or "internal-telegram-key").strip()

        if dev_key:
            repo.upsert_api_key(
                key_value=dev_key,
                name="Development",
                role="dev",
                rate_limit=1000,
                active=True,
            )
        if test_key:
            repo.upsert_api_key(
                key_value=test_key,
                name="Test Client",
                role="test",
                rate_limit=100,
                active=True,
            )
        if internal_key:
            repo.upsert_api_key(
                key_value=internal_key,
                name="Internal Telegram",
                role="internal",
                rate_limit=1000,
                active=True,
            )

    def get_api_key(self, key: str) -> Optional[dict]:
        self._ensure_default_keys()
        row = self._get_repository().get_api_key(key)
        if not row:
            return None
        return {
            "name": str(row.get("name") or ""),
            "created": str(row.get("created_at") or ""),
            "rate_limit": int(row.get("rate_limit") or 100),
            "active": bool(int(row.get("active") or 0)),
            "role": str(row.get("role") or "test"),
        }

    def is_valid(self, key: str) -> bool:
        key_info = self.get_api_key(key)
        return key_info is not None and key_info.get("active", False)

    def is_dev_key(self, key: str) -> bool:
        key_info = self.get_api_key(key)
        if not key_info:
            return False
        role = str(key_info.get("role") or "").strip().lower()
        return role in {"dev", "admin"}

    def check_rate_limit(self, api_key: str) -> bool:
        key_info = self.get_api_key(api_key)
        if not key_info:
            return False

        rate_limit = int(key_info.get("rate_limit", 100))
        now = datetime.now()
        minute_key = f"{api_key}:{now.strftime('%Y-%m-%d %H:%M')}"

        if minute_key not in self.request_counts:
            self.request_counts[minute_key] = 0

        if self.request_counts[minute_key] >= rate_limit:
            return False

        self.request_counts[minute_key] += 1
        self._cleanup_old_counts(now)
        return True

    def _cleanup_old_counts(self, now: datetime) -> None:
        cutoff_time = now - timedelta(minutes=2)
        keys_to_delete = []

        for key in list(self.request_counts.keys()):
            try:
                date_str = key.rsplit(":", 1)[-1]
                stored_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                if stored_time < cutoff_time:
                    keys_to_delete.append(key)
            except (ValueError, IndexError):
                continue

        for key in keys_to_delete:
            del self.request_counts[key]

    def add_api_key(self, key: str, name: str, rate_limit: int = 100, role: str = "test") -> None:
        self._ensure_default_keys()
        self._get_repository().upsert_api_key(
            key_value=key,
            name=name,
            role=role,
            rate_limit=max(1, int(rate_limit)),
            active=True,
        )
        logger.info("api_key.added name=%s role=%s", name, role)

    def deactivate_api_key(self, key: str) -> bool:
        key_info = self.get_api_key(key)
        if not key_info:
            return False
        self._get_repository().upsert_api_key(
            key_value=key,
            name=str(key_info.get("name") or ""),
            role=str(key_info.get("role") or "test"),
            rate_limit=int(key_info.get("rate_limit") or 100),
            active=False,
        )
        logger.info("api_key.deactivated")
        return True


api_key_manager = APIKeyManager()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> str:
    """Проверить API ключ из заголовка X-API-Key."""

    if not x_api_key:
        logger.warning("Request without API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API ключ требуется. Передайте в заголовке X-API-Key"
        )

    if not api_key_manager.is_valid(x_api_key):
        logger.warning("Invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидный или деактивированный API ключ"
        )

    if not api_key_manager.check_rate_limit(x_api_key):
        logger.warning("Rate limit exceeded for API key")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Превышен лимит запросов. Попробуйте позже"
        )

    return x_api_key


@lru_cache(maxsize=128)
def get_api_key_info(api_key: str) -> dict:
    """Получить информацию об API ключе (с кэшированием)."""
    return api_key_manager.get_api_key(api_key) or {}


def is_dev_key(api_key: str) -> bool:
    """Удобная функция для проверки dev-ключа в routes."""
    return api_key_manager.is_dev_key(api_key)
