from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import dependencies as deps
from api.main import app
from bot_agent.config import config
from api.telegram_adapter.models import TelegramAdapterResponse


class StubTelegramAdapterService:
    async def handle_update(self, _update):
        return TelegramAdapterResponse(
            ok=True,
            user_id="user-dev",
            session_id="sess-dev",
            conversation_id="conv-dev",
            answer_text="mock-answer",
            channel="telegram",
            used_mock_transport=True,
        )


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_PATH", tmp_path / "telegram_mock_routes.db", raising=False)
    monkeypatch.setattr(deps, "_identity_repository", None, raising=False)
    monkeypatch.setattr(deps, "_identity_service", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_repository", None, raising=False)
    monkeypatch.setattr(deps, "_conversation_service", None, raising=False)
    monkeypatch.setattr(deps, "_telegram_adapter_service", StubTelegramAdapterService(), raising=False)
    with TestClient(app, base_url="http://localhost") as test_client:
        yield test_client


def test_mock_route_requires_dev_key(client: TestClient) -> None:
    payload = {
        "update_id": 1,
        "telegram_user_id": "tg_1",
        "chat_id": "chat_1",
        "message_id": "msg_1",
        "text": "hello",
        "timestamp": "2026-04-25T12:00:00Z",
    }
    res = client.post(
        "/api/v1/dev/telegram/mock-update",
        headers={"X-API-Key": "test-key-001"},
        json=payload,
    )
    assert res.status_code == 403


def test_mock_route_returns_adapter_response(client: TestClient) -> None:
    payload = {
        "update_id": 1,
        "telegram_user_id": "tg_1",
        "chat_id": "chat_1",
        "message_id": "msg_1",
        "text": "hello",
        "timestamp": "2026-04-25T12:00:00Z",
    }
    res = client.post(
        "/api/v1/dev/telegram/mock-update",
        headers={"X-API-Key": "dev-key-001"},
        json=payload,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["channel"] == "telegram"
    assert body["used_mock_transport"] is True
