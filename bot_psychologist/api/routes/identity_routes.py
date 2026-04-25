"""Identity-related API routes."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_api_key
from ..dependencies import get_identity_context
from ..identity import IdentityContext

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


class LinkTelegramRequest(BaseModel):
    """Request payload for future telegram link flow."""

    code: str = Field(..., min_length=3, max_length=64)
    telegram_user_id: str = Field(..., min_length=1, max_length=64)


class LinkCodeResponse(BaseModel):
    status: str
    detail: str


@router.get("/me", summary="Resolved identity context")
async def get_me_identity(
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    return identity.model_dump()


@router.get(
    "/generate-link-code",
    response_model=LinkCodeResponse,
    summary="Generate one-time link code (stub)",
)
async def generate_link_code_stub(
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    _ = (identity, api_key)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Telegram linking: coming in next PRD",
    )


@router.post("/link-telegram", summary="Telegram account linking (stub)")
async def link_telegram_stub(
    request: LinkTelegramRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    _ = (request, identity, api_key)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Telegram linking: coming in next PRD",
    )
