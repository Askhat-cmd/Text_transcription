"""Payload adapter for Telegram mock updates."""

from __future__ import annotations

import json
import logging
from typing import Any

from .models import TelegramUpdateModel

logger = logging.getLogger(__name__)


class TelegramUpdateAdapter:
    """Converts raw mock payload into TelegramUpdateModel."""

    def parse_payload(self, payload: dict[str, Any] | str | bytes) -> TelegramUpdateModel:
        if isinstance(payload, (str, bytes)):
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise TypeError("payload must be dict/json")

        model = TelegramUpdateModel.model_validate(payload)
        logger.debug(
            "telegram.adapter.payload_parsed",
            extra={
                "update_id": model.update_id,
                "telegram_user_id_prefix": model.telegram_user_id[:6],
                "chat_id": model.chat_id,
            },
        )
        return model
