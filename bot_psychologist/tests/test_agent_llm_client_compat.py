from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.multiagent.agents.agent_llm_client import create_agent_completion


class _FakeCompletions:
    def __init__(self, *, reject_response_format: bool = False, reject_max_completion_tokens: bool = False) -> None:
        self.calls: list[dict] = []
        self.reject_response_format = reject_response_format
        self.reject_max_completion_tokens = reject_max_completion_tokens

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.reject_response_format and "response_format" in kwargs:
            raise TypeError("unexpected keyword argument 'response_format'")
        if self.reject_max_completion_tokens and "max_completion_tokens" in kwargs:
            raise TypeError("unexpected keyword argument 'max_completion_tokens'")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=5, total_tokens=12),
        )


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text="responses answer",
            usage=SimpleNamespace(input_tokens=10, output_tokens=4, total_tokens=14),
        )


class _ClientWithBoth:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())
        self.responses = _FakeResponses()


class _ClientChatOnly:
    def __init__(
        self,
        *,
        reject_response_format: bool = False,
        reject_max_completion_tokens: bool = False,
    ) -> None:
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(
                reject_response_format=reject_response_format,
                reject_max_completion_tokens=reject_max_completion_tokens,
            )
        )


class _ClientWithoutLLM:
    pass


@pytest.mark.asyncio
async def test_prefers_responses_when_supported() -> None:
    client = _ClientWithBoth()
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=123,
    )
    assert result.api_mode == "responses"
    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 0


@pytest.mark.asyncio
async def test_compat_mode_when_responses_missing() -> None:
    client = _ClientChatOnly()
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.9,
        max_tokens=321,
    )
    assert result.api_mode == "chat_completions_compat"
    req = client.chat.completions.calls[0]
    assert req["max_completion_tokens"] == 321
    assert "temperature" not in req
    assert "max_tokens" not in req


@pytest.mark.asyncio
async def test_require_json_keeps_instruction_in_compat_mode() -> None:
    client = _ClientChatOnly()
    await create_agent_completion(
        client=client,
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "return schema"}],
        require_json=True,
    )
    last_msg = str(client.chat.completions.calls[0]["messages"][-1]["content"])
    assert "Return ONLY valid JSON." in last_msg


@pytest.mark.asyncio
async def test_compat_mode_retries_without_response_format_for_old_clients() -> None:
    client = _ClientChatOnly(reject_response_format=True)
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "json please"}],
        response_format={"type": "json_object"},
    )
    assert result.api_mode == "chat_completions_compat"
    assert len(client.chat.completions.calls) == 2
    assert "response_format" in client.chat.completions.calls[0]
    assert "response_format" not in client.chat.completions.calls[1]


@pytest.mark.asyncio
async def test_compat_mode_retries_without_token_limit_when_old_sdk_rejects_max_completion_tokens() -> None:
    client = _ClientChatOnly(reject_max_completion_tokens=True)
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=77,
    )
    assert result.api_mode == "chat_completions_compat"
    assert len(client.chat.completions.calls) == 2
    assert "max_completion_tokens" in client.chat.completions.calls[0]
    assert "max_completion_tokens" not in client.chat.completions.calls[1]
    assert "max_tokens" not in client.chat.completions.calls[1]


@pytest.mark.asyncio
async def test_missing_all_capabilities_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="neither responses.create nor chat.completions.create"):
        await create_agent_completion(
            client=_ClientWithoutLLM(),
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "hello"}],
        )
