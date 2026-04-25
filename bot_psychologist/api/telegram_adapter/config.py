"""Telegram adapter runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


_ALLOWED_MODES = {"mock", "disabled", "live"}


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class TelegramAdapterSettings:
    enabled: bool = False
    mode: str = "mock"
    bot_token: str | None = None

    @classmethod
    def from_env(cls) -> "TelegramAdapterSettings":
        enabled = _parse_bool(os.getenv("TELEGRAM_ENABLED"), False)
        mode = (os.getenv("TELEGRAM_MODE") or "mock").strip().lower()
        if mode not in _ALLOWED_MODES:
            mode = "mock"
        bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() or None
        return cls(enabled=enabled, mode=mode, bot_token=bot_token)


telegram_settings = TelegramAdapterSettings.from_env()
