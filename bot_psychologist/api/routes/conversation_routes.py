"""Conversation lifecycle routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import verify_api_key
from ..conversations import ConversationContext, ConversationSummary, StartConversationRequest
from ..dependencies import get_conversation_service, get_identity_context
from ..identity import IdentityContext

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("/", response_model=list[ConversationSummary], summary="List current user conversations")
async def list_my_conversations(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    conv_service=Depends(get_conversation_service),
) -> list[ConversationSummary]:
    _ = api_key
    return await conv_service.list_conversations(
        user_id=identity.user_id,
        status=status_filter,
        limit=limit,
    )


@router.post("/new", response_model=ConversationContext, summary="Start new conversation")
async def start_new_conversation(
    body: StartConversationRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    conv_service=Depends(get_conversation_service),
) -> ConversationContext:
    _ = api_key
    return await conv_service.start_new_conversation(
        user_id=identity.user_id,
        session_id=identity.session_id,
        channel=identity.channel,
        title=body.title,
    )


@router.post("/{conversation_id}/close", summary="Close conversation")
async def close_conversation(
    conversation_id: str,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
    conv_service=Depends(get_conversation_service),
) -> dict[str, str]:
    _ = api_key
    try:
        await conv_service.close_conversation(conversation_id, identity.user_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return {"status": "closed", "conversation_id": conversation_id}

