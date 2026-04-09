"""Message handlers for Telegram adapter."""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from ..api_client.stream_consumer import consume_adaptive_stream
from ..formatters.telegram_formatter import format_for_telegram, split_long_message
from ..persistence.session_store import get_or_create_session


logger = logging.getLogger(__name__)


async def _keep_typing(bot, chat_id: int, stop_event: asyncio.Event) -> None:
    """
    Keep "typing..." visible while long backend request is running.

    Telegram clears typing status in about 5 seconds, so we refresh every 4s.
    """
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            logger.debug("send_chat_action failed", exc_info=True)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            continue


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None or update.effective_chat is None:
        return

    query = (update.message.text or "").strip()
    if not query:
        return

    user_id = str(update.effective_user.id)
    chat_id = int(update.effective_chat.id)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id, stop_typing))

    try:
        session_id = await get_or_create_session(user_id)
        full_text = await consume_adaptive_stream(
            query=query,
            user_id=user_id,
            session_id=session_id,
        )

        formatted = format_for_telegram(full_text or "Пока не удалось сформировать ответ.")
        parts = split_long_message(formatted, max_length=4096)

        for idx, part in enumerate(parts):
            await update.message.reply_text(part, parse_mode="HTML")
            if idx < len(parts) - 1:
                await asyncio.sleep(0.3)
    except Exception:
        logger.exception("Telegram message handling failed")
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте повторить.",
            parse_mode="HTML",
        )
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

