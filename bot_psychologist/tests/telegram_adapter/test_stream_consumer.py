from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import patch

import httpx
import pytest

from telegram_adapter.api_client.stream_consumer import consume_adaptive_stream


class MockResponse:
    def __init__(self, lines: list[str], *, status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://localhost")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=request,
                response=response,
            )

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class MockStreamContext:
    def __init__(self, response: MockResponse) -> None:
        self._response = response

    async def __aenter__(self) -> MockResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class MockAsyncClient:
    def __init__(self, response: MockResponse, **_kwargs) -> None:
        self._response = response

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    def stream(self, *_args, **_kwargs) -> MockStreamContext:
        return MockStreamContext(self._response)


def _mock_client_factory(lines: list[str], *, status_code: int = 200):
    response = MockResponse(lines, status_code=status_code)

    def factory(**kwargs):
        return MockAsyncClient(response, **kwargs)

    return factory


@pytest.mark.asyncio
async def test_t4_1_accumulates_all_chunks() -> None:
    lines = [
        'data: {"text":"Первый."}',
        'data: {"text":" Второй."}',
        'data: {"text":" Третий."}',
        "data: [DONE]",
    ]
    with patch("httpx.AsyncClient", _mock_client_factory(lines)):
        result = await consume_adaptive_stream("тест", "user_1", "sess_1")
    assert result == "Первый. Второй. Третий."


@pytest.mark.asyncio
async def test_t4_2_plain_text_chunks() -> None:
    lines = ["data: Привет", "data:  мир", "data: done"]
    with patch("httpx.AsyncClient", _mock_client_factory(lines)):
        result = await consume_adaptive_stream("тест", "user_1", "sess_1")
    assert result == "Привет мир"


@pytest.mark.asyncio
async def test_t4_3_ignores_sse_comments() -> None:
    lines = [": keep-alive", 'data: {"text":"Текст"}', ": ping", "data: [DONE]"]
    with patch("httpx.AsyncClient", _mock_client_factory(lines)):
        result = await consume_adaptive_stream("тест", "user_1", "sess_1")
    assert result == "Текст"


@pytest.mark.asyncio
async def test_t4_4_handles_done_variants() -> None:
    done_lines = ['data: {"text":"X"}', "data: [DONE]"]
    lower_done_lines = ['data: {"text":"X"}', "data: done"]

    with patch("httpx.AsyncClient", _mock_client_factory(done_lines)):
        first = await consume_adaptive_stream("тест", "user_1", "sess_1")
    with patch("httpx.AsyncClient", _mock_client_factory(lower_done_lines)):
        second = await consume_adaptive_stream("тест", "user_1", "sess_1")

    assert first == "X"
    assert second == "X"


@pytest.mark.asyncio
async def test_t4_5_cyrillic_preserved() -> None:
    lines = ['data: {"text":"осознание себя"}', "data: [DONE]"]
    with patch("httpx.AsyncClient", _mock_client_factory(lines)):
        result = await consume_adaptive_stream("тест", "user_1", "sess_1")
    assert result == "осознание себя"


@pytest.mark.asyncio
async def test_t4_6_raises_on_http_error() -> None:
    with patch("httpx.AsyncClient", _mock_client_factory([], status_code=500)):
        with pytest.raises(httpx.HTTPStatusError):
            await consume_adaptive_stream("тест", "user_1", "sess_1")


@pytest.mark.asyncio
async def test_done_payload_with_answer_fallback() -> None:
    payload = json.dumps({"done": True, "answer": "Финальный ответ"}, ensure_ascii=False)
    lines = [f"data: {payload}"]
    with patch("httpx.AsyncClient", _mock_client_factory(lines)):
        result = await consume_adaptive_stream("тест", "user_1", "sess_1")
    assert result == "Финальный ответ"

