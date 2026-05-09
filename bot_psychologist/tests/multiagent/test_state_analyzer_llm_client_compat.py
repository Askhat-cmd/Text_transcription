from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent


class _FakeCompletions:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=40, completion_tokens=20, total_tokens=60),
        )


class _FakeOldSdkClient:
    def __init__(self, payload: str) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload))


@pytest.mark.asyncio
async def test_state_analyzer_uses_chat_compat_when_responses_missing() -> None:
    payload = json.dumps(
        {
            "nervous_state": "window",
            "intent": "clarify",
            "openness": "mixed",
            "ok_position": "I+W+",
            "confidence": 0.78,
        }
    )
    client = _FakeOldSdkClient(payload=payload)
    agent = StateAnalyzerAgent(client=client, model="gpt-5-mini")

    snapshot = await agent.analyze("ну не знаю что сказать")

    assert snapshot.safety_flag is False
    assert agent.last_debug.get("error") is None
    assert agent.last_debug.get("api_mode") == "chat_completions_compat"
