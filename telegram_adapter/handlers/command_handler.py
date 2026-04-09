"""Telegram slash command handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..persistence.session_store import reset_session


async def handle_start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        "Привет! Я Neo MindBot — рефлективный ассистент для самоисследования.\n\n"
        "Расскажи, что у тебя сейчас происходит — я помогу разобраться.",
        parse_mode="HTML",
    )


async def handle_reset(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return
    user_id = str(update.effective_user.id)
    await reset_session(user_id)
    await update.message.reply_text(
        "Сессия сброшена. Можешь начать новый разговор.",
        parse_mode="HTML",
    )


async def handle_help(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        "<b>Доступные команды:</b>\n"
        "/start — начать разговор\n"
        "/reset — сбросить текущую сессию\n"
        "/help — показать эту справку",
        parse_mode="HTML",
    )

