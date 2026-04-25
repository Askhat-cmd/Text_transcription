"""Telegram adapter package."""

from .adapter import TelegramUpdateAdapter
from .config import TelegramAdapterSettings, telegram_settings
from .factory import build_polling_transport
from .models import TelegramAdapterResponse, TelegramUpdateModel
from .outbound import TelegramOutboundSender
from .service import TelegramAdapterService
from .transport import TelegramPollingTransport, process_raw_update

__all__ = [
    "TelegramAdapterSettings",
    "telegram_settings",
    "TelegramUpdateAdapter",
    "TelegramUpdateModel",
    "TelegramAdapterResponse",
    "TelegramAdapterService",
    "TelegramOutboundSender",
    "TelegramPollingTransport",
    "process_raw_update",
    "build_polling_transport",
]
