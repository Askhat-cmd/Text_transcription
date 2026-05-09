from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
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
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=10, total_tokens=30),
        )


class _FakeOldSdkClient:
    def __init__(self, payload: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload))


def _contract() -> WriterContract:
    thread = ThreadState(
        thread_id="th_compat",
        user_id="u1",
        core_direction="поддержка",
        phase="clarify",
        response_mode="reflect",
        response_goal="поддержка",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    bundle = MemoryBundle(conversation_context="u: привет", context_turns=3)
    return WriterContract(user_message="привет", thread_state=thread, memory_bundle=bundle)


@pytest.mark.asyncio
async def test_writer_uses_chat_compat_when_responses_missing() -> None:
    client = _FakeOldSdkClient(payload="Содержательный ответ")
    agent = WriterAgent(client=client, model="gpt-5-mini")

    text = await agent.write(_contract())

    assert text.strip() == "Содержательный ответ"
    assert agent.last_debug.get("error") is None
    assert agent.last_debug.get("fallback_used") is False
    assert agent.last_debug.get("api_mode") == "chat_completions_compat"
