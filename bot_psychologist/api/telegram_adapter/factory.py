"""Factory helpers for Telegram transport objects."""

from __future__ import annotations

from .config import TelegramAdapterSettings, telegram_settings
from .outbound import TelegramOutboundSender
from .service import TelegramAdapterService
from .transport import TelegramPollingTransport


def build_polling_transport(
    *,
    settings: TelegramAdapterSettings | None = None,
    adapter_service: TelegramAdapterService | None = None,
    outbound_sender: TelegramOutboundSender | None = None,
) -> TelegramPollingTransport:
    """Создать polling transport с готовыми зависимостями."""
    runtime_settings = settings or telegram_settings
    if not runtime_settings.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required for polling mode")

    if adapter_service is None:
        from api.dependencies import get_telegram_adapter_service

        adapter_service = get_telegram_adapter_service()

    if outbound_sender is None:
        outbound_sender = TelegramOutboundSender(runtime_settings.bot_token)

    return TelegramPollingTransport(
        bot_token=runtime_settings.bot_token,
        adapter_service=adapter_service,
        outbound_sender=outbound_sender,
        settings=runtime_settings,
    )
