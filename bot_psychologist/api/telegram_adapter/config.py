"""Telegram adapter runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


_ALLOWED_MODES = {"mock", "disabled", "polling", "webhook", "live"}


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
        enabled = _parse_bool(os.getenv("TELEGRAM_ENABLED"), False)
        mode = (os.getenv("TELEGRAM_MODE") or "mock").strip().lower()
        if mode not in _ALLOWED_MODES:
            mode = "mock"
        if mode == "live":
            # Legacy alias from previous revisions.
            mode = "polling"
        bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() or None
        webhook_url = (os.getenv("TELEGRAM_WEBHOOK_URL") or "").strip() or None
        webhook_secret = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip() or None
        polling_timeout = max(5, _parse_int(os.getenv("TELEGRAM_POLLING_TIMEOUT"), 30))
        polling_retry_delay = max(
            0.5, _parse_float(os.getenv("TELEGRAM_POLLING_RETRY_DELAY"), 5.0)
        )
        polling_max_retry_delay = max(
            polling_retry_delay,
            _parse_float(os.getenv("TELEGRAM_POLLING_MAX_RETRY_DELAY"), 60.0),
        )
        allowed_updates = _parse_allowed_updates(os.getenv("TELEGRAM_ALLOWED_UPDATES"))
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
