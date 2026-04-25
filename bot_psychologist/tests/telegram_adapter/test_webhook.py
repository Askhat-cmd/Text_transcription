from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

import pytest

from api.telegram_adapter.config import TelegramAdapterSettings
from api.telegram_adapter.models import TelegramAdapterResponse
from api.telegram_adapter.webhook_routes import router, verify_internal_hmac
import api.telegram_adapter.webhook_routes as webhook_module


class _StubService:
    async def handle_update(self, _update):
        return TelegramAdapterResponse(ok=True, answer_text="ok")


class _StubOutbound:
    def __init__(self) -> None:
        self.sent = []

    async def send_message(self, chat_id, text, parse_mode="HTML"):
        self.sent.append((chat_id, text))
        return True

    async def send_not_linked_message(self, chat_id):
        self.sent.append((chat_id, "not-linked"))
        return True


def test_verify_internal_hmac_works() -> None:
    body = {"code": "A1B2C3", "telegram_user_id": "777"}
    assert verify_internal_hmac(body=body, provided_hmac="", secret="secret") is False


def test_webhook_returns_403_on_invalid_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook_module,
        "telegram_settings",
        TelegramAdapterSettings(enabled=True, mode="webhook", bot_token="t", webhook_secret="secret"),
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[webhook_module.get_telegram_adapter_service] = lambda: _StubService()
    app.dependency_overrides[webhook_module.get_telegram_outbound_sender] = lambda: _StubOutbound()

    with TestClient(app) as client:
        payload = {
            "update_id": 1,
            "telegram_user_id": "u",
            "chat_id": "c",
            "message_id": "m",
            "text": "hello",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = client.post("/api/v1/telegram/webhook", json=payload)
        assert response.status_code == 403


def test_webhook_returns_200_on_valid_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        webhook_module,
        "telegram_settings",
        TelegramAdapterSettings(enabled=True, mode="webhook", bot_token="t", webhook_secret="secret"),
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[webhook_module.get_telegram_adapter_service] = lambda: _StubService()
    app.dependency_overrides[webhook_module.get_telegram_outbound_sender] = lambda: _StubOutbound()

    with TestClient(app) as client:
        payload = {
            "update_id": 1,
            "telegram_user_id": "u",
            "chat_id": "c",
            "message_id": "m",
            "text": "hello",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        response = client.post(
            "/api/v1/telegram/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
        )
        assert response.status_code == 200
