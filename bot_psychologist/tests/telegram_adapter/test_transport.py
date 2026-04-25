from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from api.telegram_adapter.config import TelegramAdapterSettings
from api.telegram_adapter.models import TelegramAdapterResponse
from api.telegram_adapter.transport import TelegramPollingTransport


class _StubService:
    def __init__(self, response: TelegramAdapterResponse) -> None:
        self.response = response

    async def handle_update(self, _update):
        return self.response


class _StubOutbound:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.not_linked: list[str] = []

    async def send_message(self, chat_id, text, parse_mode="HTML"):
        self.sent.append((str(chat_id), str(text)))
        return True

    async def send_not_linked_message(self, chat_id):
        self.not_linked.append(str(chat_id))
        return True


@pytest.mark.asyncio
async def test_process_update_linked_user_sends_answer() -> None:
    outbound = _StubOutbound()
    service = _StubService(TelegramAdapterResponse(ok=True, answer_text="Привет"))
    settings = TelegramAdapterSettings(enabled=True, mode="polling", bot_token="token")
    transport = TelegramPollingTransport(
        bot_token="token",
        adapter_service=service,
        outbound_sender=outbound,
        settings=settings,
    )

    raw_update = {
        "update_id": 1,
        "telegram_user_id": "u1",
        "chat_id": "c1",
        "message_id": "m1",
        "text": "hello",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await transport._process_update(raw_update)
    assert outbound.sent and outbound.sent[0][1] == "Привет"


@pytest.mark.asyncio
async def test_process_update_not_linked_sends_instruction() -> None:
    outbound = _StubOutbound()
    service = _StubService(TelegramAdapterResponse(ok=False, error="telegram_not_linked"))
    settings = TelegramAdapterSettings(enabled=True, mode="polling", bot_token="token")
    transport = TelegramPollingTransport(
        bot_token="token",
        adapter_service=service,
        outbound_sender=outbound,
        settings=settings,
    )

    raw_update = {
        "update_id": 1,
        "telegram_user_id": "u1",
        "chat_id": "c1",
        "message_id": "m1",
        "text": "hello",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await transport._process_update(raw_update)
    assert outbound.not_linked == ["c1"]


@pytest.mark.asyncio
async def test_polling_offset_increments_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    outbound = _StubOutbound()
    service = _StubService(TelegramAdapterResponse(ok=True, answer_text="ok"))
    settings = TelegramAdapterSettings(enabled=True, mode="polling", bot_token="token")
    transport = TelegramPollingTransport(
        bot_token="token",
        adapter_service=service,
        outbound_sender=outbound,
        settings=settings,
    )

    calls = {"count": 0}

    async def _poll_once(offset: int):
        calls["count"] += 1
        if calls["count"] == 1:
            return [
                {"update_id": 100, "telegram_user_id": "u", "chat_id": "c", "message_id": "m", "text": "a", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"update_id": 101, "telegram_user_id": "u", "chat_id": "c", "message_id": "m", "text": "b", "timestamp": datetime.now(timezone.utc).isoformat()},
            ]
        await transport.stop()
        return []

    monkeypatch.setattr(transport, "_poll_once", _poll_once)
    await transport.start()
    assert transport._offset == 102


@pytest.mark.asyncio
async def test_transport_does_not_start_when_disabled() -> None:
    outbound = _StubOutbound()
    service = _StubService(TelegramAdapterResponse(ok=True, answer_text="ok"))
    settings = TelegramAdapterSettings(enabled=False, mode="polling", bot_token="token")
    transport = TelegramPollingTransport(
        bot_token="token",
        adapter_service=service,
        outbound_sender=outbound,
        settings=settings,
    )
    await transport.start()
    assert outbound.sent == []
