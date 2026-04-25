"""Feedback API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from bot_agent.conversation_memory import get_conversation_memory

from ..auth import verify_api_key
from ..dependencies import get_identity_context
from ..identity import IdentityContext
from ..models import FeedbackRequest, FeedbackResponse
from .common import logger

router = APIRouter(prefix="/api/v1", tags=["bot"])


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit feedback",
    description="Submit user feedback for an answer",
)
async def submit_feedback(
    request: FeedbackRequest,
    identity: IdentityContext = Depends(get_identity_context),
    api_key: str = Depends(verify_api_key),
):
    logger.info("Feedback received: user=%s type=%s", identity.user_id, request.feedback.value)

    try:
        memory = get_conversation_memory(identity.user_id)
        memory.add_feedback(
            turn_index=request.turn_index,
            feedback=request.feedback.value,
            rating=request.rating,
        )

        return FeedbackResponse(
            status="success",
            message="Feedback saved",
            user_id=identity.user_id,
            turn_index=request.turn_index,
        )
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Turn #{request.turn_index} not found",
        )
    except Exception as exc:
        logger.error("Feedback submit error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

