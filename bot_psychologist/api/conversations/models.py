"""Pydantic models for conversation layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ConversationChannel = Literal["web", "telegram", "api"]
ConversationStatus = Literal["active", "paused", "closed", "archived"]


class ConversationRecord(BaseModel):
    """Internal DB record for a conversation."""

    id: str
    user_id: str
    session_id: str
    channel: ConversationChannel
    status: ConversationStatus
    title: Optional[str] = None
    started_at: datetime
    last_message_at: datetime
    ended_at: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0


class ConversationContext(BaseModel):
    """Public conversation context passed to runtime/services."""

    conversation_id: str
    user_id: str
    session_id: str
    channel: ConversationChannel
    status: ConversationStatus = "active"
    started_at: datetime
    is_new: bool = False


class StartConversationRequest(BaseModel):
    """Request payload for explicit conversation start."""

    title: Optional[str] = Field(default=None, max_length=200)


class ConversationSummary(BaseModel):
    """Compact conversation payload for list endpoints."""

    conversation_id: str
    status: ConversationStatus
    started_at: datetime
    last_message_at: datetime
    title: Optional[str] = None
    message_count: int = 0

