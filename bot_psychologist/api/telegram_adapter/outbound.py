"""Outbound sender for Telegram Bot API."""

from __future__ import annotations

import logging

import httpx


logger = logging.getLogger(__name__)


class TelegramOutboundSender:
    """Отправляет сообщения пользователям через Telegram Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        parse_mode: str = "HTML",
    ) -> bool:
        """Отправить текстовое сообщение и вернуть флаг успеха."""
        if not str(chat_id).strip() or not str(text).strip():
            return False

        url = self.BASE_URL.format(token=self._token, method="sendMessage")
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            return True
        except (httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException) as exc:
            logger.warning("telegram.outbound.send_failed: %s", exc)
            return False

    async def send_not_linked_message(self, chat_id: str | int) -> bool:
        """Стандартный ответ для незалинкованного пользователя."""
        text = (
            "Аккаунт не привязан. Зарегистрируйтесь в веб-интерфейсе и "
            "введите команду /link <код>."
        )
        return await self.send_message(chat_id=chat_id, text=text)
