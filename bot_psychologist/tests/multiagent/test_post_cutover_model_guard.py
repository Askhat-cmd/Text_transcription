from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeCompletions:
    async def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=8, total_tokens=18),
        )


class _FakeResponses:
    async def create(self, **_kwargs):
        return SimpleNamespace(
            output_text="ok",
            usage=SimpleNamespace(input_tokens=12, output_tokens=7, total_tokens=19),
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())
        self.responses = _FakeResponses()


def _writer_contract() -> WriterContract:
    thread = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="anxiety",
        phase="clarify",
        response_mode="reflect",
        response_goal="support",
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
    return WriterContract(user_message="hello", thread_state=thread, memory_bundle=memory)


@pytest.mark.asyncio
async def test_post_cutover_writer_model_hot_swap_guard() -> None:
    agent = WriterAgent(client=_FakeClient())
    try:
        set_model_for_agent("writer", "gpt-5-mini")
        await agent._call_llm(_writer_contract())
        assert agent.last_debug["model"] == "gpt-5-mini"
        assert agent.last_debug["api_mode"] == "responses"

        set_model_for_agent("writer", "gpt-4o-mini")
        await agent._call_llm(_writer_contract())
        assert agent.last_debug["model"] == "gpt-4o-mini"
        assert agent.last_debug["api_mode"] == "chat_completions"
    finally:
        reset_model_for_agent("writer")
