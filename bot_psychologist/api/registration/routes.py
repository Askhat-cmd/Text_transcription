"""HTTP routes for registration and access control."""

from __future__ import annotations

import hmac
import hashlib
import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies import get_current_session_context, get_registration_service

from .models import (
    ConfirmLinkRequest,
    ConfirmLinkResponse,
    InviteKeyCreateRequest,
    InviteKeyCreateResponse,
    LinkCodeResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    SessionContext,
)
from .service import RegistrationService, RegistrationServiceError


router = APIRouter(prefix="/api/v1/auth", tags=["registration"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["registration-admin"])


def _verify_hmac_signature(body: dict, provided_hmac: str | None, secret: str) -> bool:
    if not provided_hmac:
        return False
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hmac.strip().lower())


@router.post("/register", response_model=RegisterResponse)
async def register(
    body: RegisterRequest,
    registration_service: RegistrationService = Depends(get_registration_service),
) -> RegisterResponse:
    try:
        return await registration_service.register(username=body.username, invite_key=body.invite_key)
    except RegistrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    registration_service: RegistrationService = Depends(get_registration_service),
) -> LoginResponse:
    try:
        return await registration_service.login(username=body.username, access_key=body.access_key)
    except RegistrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/telegram/link-code", response_model=LinkCodeResponse)
async def create_telegram_link_code(
    session: SessionContext = Depends(get_current_session_context),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> LinkCodeResponse:
    try:
        return await registration_service.create_link_code(session_token=session.session_token)
    except RegistrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/telegram/confirm-link", response_model=ConfirmLinkResponse)
async def confirm_telegram_link(
    body: ConfirmLinkRequest,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    x_request_hmac: str | None = Header(default=None, alias="X-Request-HMAC"),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> ConfirmLinkResponse:
    internal_key = (os.getenv("INTERNAL_TELEGRAM_KEY") or "internal-telegram-key").strip()
    provided_key = (x_internal_key or "").strip()
    if not internal_key or not provided_key or not hmac.compare_digest(internal_key, provided_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal key")

    payload = body.model_dump(mode="json")
    if not _verify_hmac_signature(payload, x_request_hmac, internal_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request signature")

    result = await registration_service.confirm_telegram_link(
        code=body.code,
        telegram_user_id=body.telegram_user_id,
    )
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error_message)
    return result


@admin_router.post("/invite-keys", response_model=InviteKeyCreateResponse)
async def create_invite_key(
    body: InviteKeyCreateRequest,
    session: SessionContext = Depends(get_current_session_context),
    registration_service: RegistrationService = Depends(get_registration_service),
) -> InviteKeyCreateResponse:
    try:
        return await registration_service.create_invite_key(
            admin_session_token=session.session_token,
            role_grant=body.role_grant,
            expires_in_days=body.expires_in_days,
        )
    except RegistrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
