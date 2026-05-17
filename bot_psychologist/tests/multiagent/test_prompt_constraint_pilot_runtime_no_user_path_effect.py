from __future__ import annotations

import sys
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _contract() -> WriterContract:
    return WriterContract(
        user_message="test question",
        thread_state=ThreadState(
            thread_id="t1",
            user_id="u1",
            core_direction="support",
            phase="clarify",
            response_mode="reflect",
        ),
        memory_bundle=MemoryBundle(conversation_context="ctx", has_relevant_knowledge=False, context_turns=1),
    )


@pytest.mark.asyncio
async def test_writer_prompt_same_when_pilot_not_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []

    async def _fake_completion(**kwargs):
        messages = kwargs.get("messages") or []
        user_prompt = str(messages[-1]["content"]) if messages else ""
        prompts.append(user_prompt)
        return SimpleNamespace(
            text="ok",
            tokens_prompt=1,
            tokens_completion=1,
            tokens_total=2,
            api_mode="responses",
        )

    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    agent = WriterAgent(client=object(), model="gpt-5-mini")
    await agent._call_llm(_contract(), prompt_constraint_decision=None)
    await agent._call_llm(
        _contract(),
        prompt_constraint_decision={"activation_mode": "shadow_only", "apply_to_writer_prompt": False},
    )

    assert len(prompts) == 2
    assert prompts[0] == prompts[1]
    assert "PILOT PROMPT CONSTRAINTS:" not in prompts[1]
