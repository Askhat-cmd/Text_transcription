from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.llm_answerer import LLMAnswerer


class AsyncItems:
    def __init__(self, items):
        self._items = list(items)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def make_chat_chunk(
    token: str,
    *,
    finish_reason: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
):
    usage = None
    if prompt_tokens is not None or completion_tokens is not None:
        usage = SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=token), finish_reason=finish_reason)],
        usage=usage,
    )


def make_reasoning_event(token: str):
    return SimpleNamespace(delta=token, output_text=None, usage=None)


@pytest.fixture
def answerer(monkeypatch):
    instance = LLMAnswerer.__new__(LLMAnswerer)
    instance.api_key = "test"
    instance.client = None
    instance.async_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace()),
        responses=SimpleNamespace(),
    )
    monkeypatch.setattr(instance, "build_system_prompt", lambda: "system")
    monkeypatch.setattr(
        instance,
        "build_context_prompt",
        lambda blocks, user_question, conversation_history=None: "context",
    )
    return instance


async def collect_stream_tokens(answerer: LLMAnswerer, *, model: str) -> str:
    tokens: list[str] = []
    async for token in answerer.answer_stream(
        "вопрос",
        blocks=[SimpleNamespace()],
        model=model,
    ):
        tokens.append(token)
    return "".join(tokens)


@pytest.mark.asyncio
async def test_finish_reason_stop_logs_info(monkeypatch, caplog, answerer) -> None:
    monkeypatch.setattr(config, "supports_custom_temperature", lambda model=None: True)
    answerer.async_client.chat.completions.create = AsyncMock(
        return_value=AsyncItems(
            [
                make_chat_chunk("Полный "),
                make_chat_chunk("ответ", finish_reason="stop", prompt_tokens=10, completion_tokens=2),
            ]
        )
    )

    with caplog.at_level(logging.INFO, logger="bot_agent.llm_answerer"):
        result = await collect_stream_tokens(answerer, model="gpt-4o")

    assert result == "Полный ответ"
    assert any("finish_reason=stop" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_finish_reason_length_logs_warning(monkeypatch, caplog, answerer) -> None:
    monkeypatch.setattr(config, "supports_custom_temperature", lambda model=None: True)
    answerer.async_client.chat.completions.create = AsyncMock(
        return_value=AsyncItems(
            [
                make_chat_chunk("Обрезан"),
                make_chat_chunk("ный", finish_reason="length", prompt_tokens=100, completion_tokens=50),
            ]
        )
    )

    with caplog.at_level(logging.WARNING, logger="bot_agent.llm_answerer"):
        _ = await collect_stream_tokens(answerer, model="gpt-4o")

    assert any("STREAM CUT BY TOKEN LIMIT" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_missing_finish_reason_logs_warning(monkeypatch, caplog, answerer) -> None:
    monkeypatch.setattr(config, "supports_custom_temperature", lambda model=None: True)
    answerer.async_client.chat.completions.create = AsyncMock(
        return_value=AsyncItems([make_chat_chunk("Токен"), make_chat_chunk(" без маркера")])
    )

    with caplog.at_level(logging.WARNING, logger="bot_agent.llm_answerer"):
        _ = await collect_stream_tokens(answerer, model="gpt-4o")

    assert any("without finish_reason" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_reasoning_stream_logs_completion(monkeypatch, caplog, answerer) -> None:
    monkeypatch.setattr(config, "supports_custom_temperature", lambda model=None: False)
    answerer.async_client.responses.create = AsyncMock(
        return_value=AsyncItems([make_reasoning_event("A"), make_reasoning_event("B")])
    )

    with caplog.at_level(logging.INFO, logger="bot_agent.llm_answerer"):
        result = await collect_stream_tokens(answerer, model="gpt-5-mini")

    assert result == "AB"
    assert any("reasoning stream done" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_answer_stream_with_empty_blocks_yields_fallback(answerer) -> None:
    tokens: list[str] = []
    async for token in answerer.answer_stream("вопрос", blocks=[]):
        tokens.append(token)
    result = "".join(tokens).lower()
    assert "не нашёл" in result or "релевантного" in result
