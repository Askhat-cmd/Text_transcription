from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.agent_llm_config import (
    reset_model_for_agent,
    set_model_for_agent,
)
from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeCompletions:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=8, total_tokens=18),
        )


class _FakeResponses:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=12, output_tokens=7, total_tokens=19),
        )


class _FakeClient:
    def __init__(self, payload: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload))
        self.responses = _FakeResponses(payload=payload)


def _writer_contract() -> WriterContract:
    thread = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="тревога",
        phase="clarify",
        response_mode="reflect",
        response_goal="поддержка",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
    )
    memory = MemoryBundle(
        conversation_context="ctx",
        user_profile=UserProfile(patterns=["p"], values=["v"]),
        semantic_hits=[],
        has_relevant_knowledge=False,
        context_turns=1,
    )
    return WriterContract(user_message="привет", thread_state=thread, memory_bundle=memory)


@pytest.mark.asyncio
async def test_writer_hot_swap_applies_on_next_call() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client)

    set_model_for_agent("writer", "gpt-5-mini")
    await agent._call_llm(_writer_contract())
    assert agent.last_debug["model"] == "gpt-5-mini"
    assert agent.last_debug["api_mode"] == "responses"

    set_model_for_agent("writer", "gpt-4o-mini")
    await agent._call_llm(_writer_contract())
    assert agent.last_debug["model"] == "gpt-4o-mini"
    assert agent.last_debug["api_mode"] == "chat_completions"

    reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_state_analyzer_hot_swap_applies_on_next_call() -> None:
    payload = json.dumps(
        {
            "nervous_state": "window",
            "intent": "clarify",
            "openness": "open",
            "ok_position": "I+W+",
            "confidence": 0.8,
        }
    )
    client = _FakeClient(payload)
    agent = StateAnalyzerAgent(client=client)

    set_model_for_agent("state_analyzer", "gpt-5-nano")
    await agent.analyze("неоднозначный вопрос")
    assert agent.last_debug["model"] == "gpt-5-nano"
    assert agent.last_debug["api_mode"] == "responses"

    set_model_for_agent("state_analyzer", "gpt-4o-mini")
    await agent.analyze("неоднозначный вопрос")
    assert agent.last_debug["model"] == "gpt-4o-mini"
    assert agent.last_debug["api_mode"] == "chat_completions"

    reset_model_for_agent("state_analyzer")
