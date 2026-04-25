from __future__ import annotations

import asyncio

import httpx
import pytest

from api.telegram_adapter.outbound import TelegramOutboundSender


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("bad", request=httpx.Request("POST", "http://x"), response=httpx.Response(self.status_code))


class _FakeClient:
    def __init__(self, *, mode: str = "ok") -> None:
        self.mode = mode
        self.last_json = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, _url, json=None):
        self.last_json = json
        if self.mode == "network_error":
            raise httpx.NetworkError("network")
        if self.mode == "http_error":
            return _FakeResponse(status_code=500)
        return _FakeResponse(status_code=200)


@pytest.mark.asyncio
async def test_send_message_returns_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(mode="ok")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake)

    sender = TelegramOutboundSender("token")
    result = await sender.send_message("1", "hello")
    assert result is True


@pytest.mark.asyncio
async def test_send_message_returns_false_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(mode="http_error")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake)

    sender = TelegramOutboundSender("token")
    result = await sender.send_message("1", "hello")
    assert result is False


@pytest.mark.asyncio
async def test_send_message_returns_false_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(mode="network_error")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake)

    sender = TelegramOutboundSender("token")
    result = await sender.send_message("1", "hello")
    assert result is False


@pytest.mark.asyncio
async def test_send_not_linked_contains_link(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(mode="ok")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake)

    sender = TelegramOutboundSender("token")
    result = await sender.send_not_linked_message("1")
    assert result is True
    assert "/link" in str(fake.last_json.get("text"))
