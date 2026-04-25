"""Data models for Telegram adapter contract."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TelegramUpdateModel(BaseModel):
    update_id: int
    telegram_user_id: str = Field(..., min_length=1)
    chat_id: str = Field(..., min_length=1)
    message_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    username: str | None = None
    language_code: str | None = None
    timestamp: datetime


class TelegramAdapterResponse(BaseModel):
    ok: bool
    user_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    channel: str = "telegram"
    answer_text: str = ""
    used_mock_transport: bool = True
    error: str | None = None
