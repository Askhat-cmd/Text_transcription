"""Telegram webhook routes (optional mode)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status

from api.dependencies import get_telegram_adapter_service, get_telegram_outbound_sender

from .config import telegram_settings
from .outbound import TelegramOutboundSender
from .service import TelegramAdapterService
from .transport import process_raw_update


router = APIRouter(prefix="/api/v1/telegram", tags=["telegram-webhook"])


@router.post("/webhook")
async def telegram_webhook(
    payload: dict[str, Any] = Body(...),
    x_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    adapter_service: TelegramAdapterService = Depends(get_telegram_adapter_service),
    outbound_sender: TelegramOutboundSender = Depends(get_telegram_outbound_sender),
) -> dict[str, bool]:
    if telegram_settings.mode != "webhook":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook mode is disabled")

    expected_secret = telegram_settings.webhook_secret or ""
    supplied_secret = (x_secret or "").strip()
    if not expected_secret or not hmac.compare_digest(expected_secret, supplied_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    asyncio.create_task(
        process_raw_update(
            raw_update=payload,
            adapter_service=adapter_service,
            outbound_sender=outbound_sender,
        )
    )
    return {"ok": True}


def verify_internal_hmac(
    *,
    body: dict[str, Any],
    provided_hmac: str | None,
    secret: str,
) -> bool:
    """Проверка HMAC подписи для internal endpoints."""
    provided = (provided_hmac or "").strip().lower()
    if not provided:
        return False
    payload_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)
