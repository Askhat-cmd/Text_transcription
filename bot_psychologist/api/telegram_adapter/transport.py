"""Telegram long-polling transport layer."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from .adapter import TelegramUpdateAdapter
from .config import TelegramAdapterSettings
from .outbound import TelegramOutboundSender
from .service import TelegramAdapterService


logger = logging.getLogger(__name__)


def _build_get_updates_url(bot_token: str) -> str:
    return f"https://api.telegram.org/bot{bot_token}/getUpdates"


async def process_raw_update(
    *,
    raw_update: dict[str, Any],
    adapter_service: TelegramAdapterService,
    outbound_sender: TelegramOutboundSender,
) -> None:
    """Обработать raw update без бизнес-логики в transport/webhook."""
    try:
        update = TelegramUpdateAdapter().parse_payload(raw_update)
    except Exception as exc:
        logger.warning("telegram.transport.parse_failed: %s", exc)
        return

    try:
        response = await adapter_service.handle_update(update)
    except Exception as exc:
        logger.warning("telegram.transport.handle_failed: %s", exc)
        return

    if response.ok:
        text = (response.answer_text or "").strip()
        if text:
            await outbound_sender.send_message(chat_id=update.chat_id, text=text)
        return

    if response.error == "telegram_not_linked":
        await outbound_sender.send_not_linked_message(chat_id=update.chat_id)
        return

    fallback_text = (response.answer_text or "").strip()
    if fallback_text:
        await outbound_sender.send_message(chat_id=update.chat_id, text=fallback_text)
    elif response.error:
        logger.warning("telegram.transport.update_error: %s", response.error)


class TelegramPollingTransport:
    """Long-polling worker. Только получение update и делегирование."""

    def __init__(
        self,
        *,
        bot_token: str,
        adapter_service: TelegramAdapterService,
        outbound_sender: TelegramOutboundSender,
        settings: TelegramAdapterSettings,
    ) -> None:
        self._bot_token = bot_token
        self._adapter_service = adapter_service
        self._outbound_sender = outbound_sender
        self._settings = settings
        self._stop_event = asyncio.Event()
        self._offset = 0

    async def start(self) -> None:
        """Запустить polling loop."""
        if (not self._settings.enabled) or self._settings.mode != "polling":
            logger.info("telegram.transport.skipped")
            return

        delay = float(self._settings.polling_retry_delay)
        logger.info("telegram.transport.polling_started")
        while not self._stop_event.is_set():
            try:
                updates = await self._poll_once(self._offset)
                delay = float(self._settings.polling_retry_delay)
                if updates:
                    max_update_id = max(
                        int(update.get("update_id", 0))
                        for update in updates
                        if isinstance(update, dict)
                    )
                    if max_update_id:
                        self._offset = max_update_id + 1

                for raw_update in updates:
                    if self._stop_event.is_set():
                        break
                    if not isinstance(raw_update, dict):
                        continue
                    await process_raw_update(
                        raw_update=raw_update,
                        adapter_service=self._adapter_service,
                        outbound_sender=self._outbound_sender,
                    )
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                logger.warning(
                    "telegram.transport.network_error retry_in=%.1f: %s", delay, exc
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, float(self._settings.polling_max_retry_delay))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("telegram.transport.unexpected_error: %s", exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, float(self._settings.polling_max_retry_delay))

        logger.info("telegram.transport.polling_stopped")

    async def stop(self) -> None:
        """Остановить polling loop."""
        self._stop_event.set()

    async def _poll_once(self, offset: int) -> list[dict[str, Any]]:
        """Получить пакет апдейтов от Telegram API."""
        params = {
            "timeout": self._settings.polling_timeout,
            "offset": max(0, int(offset)),
            "allowed_updates": json.dumps(self._settings.allowed_updates),
        }
        url = _build_get_updates_url(self._bot_token)
        async with httpx.AsyncClient(timeout=self._settings.polling_timeout + 10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            return []
        result = payload.get("result")
        if not isinstance(result, list):
            return []
        return [item for item in result if isinstance(item, dict)]

    async def _process_update(self, raw_update: dict[str, Any]) -> None:
        """Прокси-метод для unit тестов."""
        await process_raw_update(
            raw_update=raw_update,
            adapter_service=self._adapter_service,
            outbound_sender=self._outbound_sender,
        )
