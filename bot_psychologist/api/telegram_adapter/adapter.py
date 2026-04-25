"""Payload adapter for Telegram updates."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from .models import TelegramUpdateModel

logger = logging.getLogger(__name__)


class TelegramUpdateAdapter:
    """Converts raw Telegram payload into TelegramUpdateModel."""

    def parse_payload(self, payload: dict[str, Any] | str | bytes) -> TelegramUpdateModel:
        if isinstance(payload, (str, bytes)):
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise TypeError("payload must be dict/json")

        normalized = self._normalize_payload(payload)
        model = TelegramUpdateModel.model_validate(normalized)
        logger.debug(
            "telegram.adapter.payload_parsed",
            extra={
                "update_id": model.update_id,
                "telegram_user_id_prefix": model.telegram_user_id[:6],
                "chat_id": model.chat_id,
            },
        )
        return model

    @staticmethod
    def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        # Contract mode from PRD-015A tests.
        if "chat_id" in payload and "message_id" in payload:
            normalized = dict(payload)
            if "timestamp" not in normalized:
                normalized["timestamp"] = datetime.now(timezone.utc).isoformat()
            return normalized

        # Native Telegram update shape.
        message = payload.get("message") or payload.get("edited_message")
        if not isinstance(message, dict):
            raise ValueError("telegram update does not contain message")
        user = message.get("from") or {}
        chat = message.get("chat") or {}

        timestamp: Any = payload.get("timestamp")
        date_value = message.get("date")
        if timestamp is None and date_value is not None:
            try:
                timestamp = datetime.fromtimestamp(int(date_value), tz=timezone.utc).isoformat()
            except (TypeError, ValueError):
                timestamp = None
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "update_id": payload.get("update_id"),
            "telegram_user_id": str(user.get("id") or "").strip(),
            "chat_id": str(chat.get("id") or "").strip(),
            "message_id": str(message.get("message_id") or "").strip(),
            "text": str(message.get("text") or "").strip(),
            "username": user.get("username"),
            "language_code": user.get("language_code"),
            "timestamp": timestamp,
        }
