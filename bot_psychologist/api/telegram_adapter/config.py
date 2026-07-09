"""Telegram adapter runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


_ALLOWED_MODES = {"mock", "disabled", "polling", "webhook", "live"}
TELEGRAM_ENABLED_DEFAULT = False
TELEGRAM_MODE_DEFAULT = "mock"
TELEGRAM_WEBHOOK_URL_DEFAULT: Optional[str] = None
TELEGRAM_POLLING_TIMEOUT_DEFAULT = 30
TELEGRAM_POLLING_RETRY_DELAY_DEFAULT = 5.0
TELEGRAM_POLLING_MAX_RETRY_DELAY_DEFAULT = 60.0
TELEGRAM_ALLOWED_UPDATES_DEFAULT: tuple[str, ...] = ("message",)


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_allowed_updates(value: str | None) -> list[str]:
    if not value:
        return ["message"]
    parsed = [item.strip() for item in value.split(",")]
    return [item for item in parsed if item] or ["message"]


@dataclass(frozen=True)
class TelegramAdapterSettings:
    enabled: bool = False
    mode: str = "mock"  # mock | disabled | polling | webhook
    bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    polling_timeout: int = 30
    polling_retry_delay: float = 5.0
    polling_max_retry_delay: float = 60.0
    allowed_updates: list[str] = field(default_factory=lambda: ["message"])

    @classmethod
    def from_env(cls) -> "TelegramAdapterSettings":
        # PRD-047.41: frozen constants until Telegram deployment gets its own PRD.
        enabled = TELEGRAM_ENABLED_DEFAULT
        mode = TELEGRAM_MODE_DEFAULT
        if mode not in _ALLOWED_MODES:
            mode = "mock"
        bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() or None
        webhook_url = TELEGRAM_WEBHOOK_URL_DEFAULT
        webhook_secret = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip() or None
        polling_timeout = max(5, TELEGRAM_POLLING_TIMEOUT_DEFAULT)
        polling_retry_delay = max(0.5, TELEGRAM_POLLING_RETRY_DELAY_DEFAULT)
        polling_max_retry_delay = max(
            polling_retry_delay,
            TELEGRAM_POLLING_MAX_RETRY_DELAY_DEFAULT,
        )
        allowed_updates = list(TELEGRAM_ALLOWED_UPDATES_DEFAULT)
        return cls(
            enabled=enabled,
            mode=mode,
            bot_token=bot_token,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            polling_timeout=polling_timeout,
            polling_retry_delay=polling_retry_delay,
            polling_max_retry_delay=polling_max_retry_delay,
            allowed_updates=allowed_updates,
        )


telegram_settings = TelegramAdapterSettings.from_env()
