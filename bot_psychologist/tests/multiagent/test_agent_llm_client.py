from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.agent_llm_client import (
    AgentLLMResult,
    create_agent_completion,
    messages_to_input,
)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="chat answer"))],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
        )


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.use_output_array = False
        self.missing_total = False

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = (
            SimpleNamespace(input_tokens=13, output_tokens=9)
            if self.missing_total
            else SimpleNamespace(input_tokens=13, output_tokens=9, total_tokens=22)
        )
        if self.use_output_array:
            output = [
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", text="responses from output array")],
                )
            ]
            return SimpleNamespace(output=output, usage=usage)
        return SimpleNamespace(output_text="responses answer", usage=usage)


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())
        self.responses = _FakeResponses()


@pytest.mark.asyncio
async def test_create_agent_completion_uses_chat_for_gpt4o() -> None:
    client = _FakeClient()
    result = await create_agent_completion(
        client=client,
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        temperature=0.7,
        max_tokens=120,
        response_format={"type": "json_object"},
    )

    assert isinstance(result, AgentLLMResult)
    assert result.api_mode == "chat_completions"
    assert result.text == "chat answer"
    assert result.tokens_prompt == 11
    assert result.tokens_completion == 7
    assert result.tokens_total == 18
    assert len(client.chat.completions.calls) == 1
    assert len(client.responses.calls) == 0
    req = client.chat.completions.calls[0]
    assert req["temperature"] == pytest.approx(0.7, abs=1e-9)
    assert req["max_tokens"] == 120
    assert req["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_create_agent_completion_uses_responses_for_gpt5() -> None:
    client = _FakeClient()
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        temperature=0.7,
        max_tokens=222,
    )

    assert result.api_mode == "responses"
    assert result.text == "responses answer"
    assert result.tokens_prompt == 13
    assert result.tokens_completion == 9
    assert result.tokens_total == 22
    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 0
    req = client.responses.calls[0]
    assert req["max_output_tokens"] == 222
    assert "temperature" not in req
    assert "max_tokens" not in req


@pytest.mark.asyncio
async def test_create_agent_completion_responses_total_calculated_when_missing() -> None:
    client = _FakeClient()
    client.responses.missing_total = True
    result = await create_agent_completion(
        client=client,
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "u"}],
        max_tokens=20,
    )
    assert result.tokens_total == 22


@pytest.mark.asyncio
async def test_create_agent_completion_responses_output_array_supported() -> None:
    client = _FakeClient()
    client.responses.use_output_array = True
    result = await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "u"}],
    )
    assert result.text == "responses from output array"


@pytest.mark.asyncio
async def test_create_agent_completion_require_json_appends_instruction() -> None:
    client = _FakeClient()
    await create_agent_completion(
        client=client,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "u"}],
        require_json=True,
    )
    sent_input = str(client.responses.calls[0]["input"])
    assert "Return ONLY a valid JSON object." in sent_input


def test_messages_to_input_formats_roles() -> None:
    text = messages_to_input(
        [
            {"role": "system", "content": "A"},
            {"role": "user", "content": "B"},
        ]
    )
    assert "SYSTEM:" in text
    assert "USER:" in text
    assert "A" in text
    assert "B" in text
