"""Pydantic models for API identity layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


IdentityProvider = Literal["web", "telegram", "api", "legacy"]
IdentityChannel = Literal["web", "telegram", "api"]


class UserRecord(BaseModel):
    """Canonical user record."""

    id: str
    created_at: datetime
    updated_at: datetime
    status: str = "active"
    canonical_name: Optional[str] = None
    timezone: str = "UTC"
    language: str = "ru"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class LinkedIdentity(BaseModel):
    """External identity linked to canonical user."""

    id: str
    user_id: str
    provider: IdentityProvider
    external_id: str
    verified_at: Optional[datetime] = None
    created_at: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SessionRecord(BaseModel):
    """Identity-level session record."""

    session_id: str
    user_id: str
    channel: IdentityChannel = "web"
    device_fingerprint: Optional[str] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


# Backward-compatible alias for PRD naming.
Session = SessionRecord


class IdentityContext(BaseModel):
    """Resolved identity context used by API routes."""

    user_id: str
    session_id: str
    conversation_id: str
    channel: IdentityChannel = "web"
    is_anonymous: bool = True
    created_new_user: bool = False
    provider: IdentityProvider = "web"
    external_id: Optional[str] = None
    role: str = "anonymous"
    username: Optional[str] = None
    is_registered: bool = False
