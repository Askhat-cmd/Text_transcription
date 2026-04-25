"""Dev-only mock routes for Telegram adapter contract."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from ..telegram_adapter.adapter import TelegramUpdateAdapter
from ..telegram_adapter.models import TelegramAdapterResponse

from ..auth import is_dev_key, verify_api_key
from ..dependencies import get_telegram_adapter_service

router = APIRouter(prefix="/api/v1/dev/telegram", tags=["telegram-dev"])


@router.post("/mock-update", response_model=TelegramAdapterResponse)
async def post_mock_update(
    payload: dict[str, Any] = Body(...),
    api_key: str = Depends(verify_api_key),
    telegram_service=Depends(get_telegram_adapter_service),
) -> TelegramAdapterResponse:
    if not is_dev_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev endpoint is available only for dev API key",
        )

    try:
        update = TelegramUpdateAdapter().parse_payload(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid telegram mock payload: {exc}",
        ) from exc

    return await telegram_service.handle_update(update)
