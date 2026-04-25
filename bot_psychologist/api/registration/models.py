"""Pydantic models for registration and access flows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


UserRole = Literal["admin", "user", "trial", "blocked", "anonymous", "internal", "dev", "test"]


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    invite_key: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("username is required")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if any(ch not in allowed for ch in normalized):
            raise ValueError("username contains invalid characters")
        return normalized


class RegisterResponse(BaseModel):
    user_id: str
    access_key: str
    role: str


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    access_key: str = Field(..., min_length=8, max_length=256)

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class LoginResponse(BaseModel):
    user_id: str
    session_token: str
    role: str
    username: str
    expires_at: datetime


class LinkCodeResponse(BaseModel):
    code: str
    expires_in_seconds: int = 900


class ConfirmLinkRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=64)
    telegram_user_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("telegram_user_id")
    @classmethod
    def _normalize_tg_user(cls, value: str) -> str:
        return value.strip()


class ConfirmLinkResponse(BaseModel):
    ok: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    error_message: Optional[str] = None


class InviteKeyCreateRequest(BaseModel):
    role_grant: Literal["admin", "user", "trial"] = "user"
    expires_in_days: int = Field(default=7, ge=1, le=3650)


class InviteKeyCreateResponse(BaseModel):
    key_value: str
    expires_at: datetime


class SessionContext(BaseModel):
    session_token: str
    user_id: str
    username: str
    role: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None

