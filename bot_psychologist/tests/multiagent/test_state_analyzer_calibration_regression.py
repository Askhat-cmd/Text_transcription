from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent


class _FakeResponses:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    async def create(self, **kwargs):  # noqa: ANN003
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=10, output_tokens=10, total_tokens=20),
        )


class _FakeClient:
    def __init__(self, payload: str) -> None:
        self.responses = _FakeResponses(payload)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=None))


@pytest.mark.asyncio
async def test_low_resource_contact_ru_detected_as_contact_and_hypo() -> None:
    agent = StateAnalyzerAgent(client=None, model="gpt-5-nano")
    agent._get_client = lambda: None  # type: ignore[method-assign]
    snapshot = await agent.analyze("Я очень устал. Не хочу советов, просто скажи пару спокойных слов.")
    assert snapshot.intent == "contact"
    assert snapshot.nervous_state == "hypo"


@pytest.mark.asyncio
async def test_low_resource_contact_en_detected_as_contact_and_hypo() -> None:
    agent = StateAnalyzerAgent(client=None, model="gpt-5-nano")
    agent._get_client = lambda: None  # type: ignore[method-assign]
    snapshot = await agent.analyze("I am exhausted. No analysis please, just two calm words and stay with me.")
    assert snapshot.intent == "contact"
    assert snapshot.nervous_state == "hypo"


@pytest.mark.asyncio
async def test_solution_cases_have_solution_intent() -> None:
    agent = StateAnalyzerAgent(client=None, model="gpt-5-nano")
    agent._get_client = lambda: None  # type: ignore[method-assign]
    ru = await agent.analyze("Какой один конкретный шаг мне сделать сегодня?")
    en = await agent.analyze("What one concrete step can I do today to move forward?")
    assert ru.intent == "solution"
    assert en.intent == "solution"
    assert ru.nervous_state == "window"
    assert en.nervous_state == "window"


@pytest.mark.asyncio
async def test_clarify_cases_keep_clarify_and_confidence_ge_06() -> None:
    payload = json.dumps(
        {
            "nervous_state": "window",
            "intent": "clarify",
            "openness": "mixed",
            "ok_position": "I-W+",
            "confidence": 0.72,
        }
    )
    agent = StateAnalyzerAgent(client=_FakeClient(payload), model="gpt-5-nano")
    ru = await agent.analyze("Со мной что-то не так, но я не могу понять что.")
    en = await agent.analyze("Something feels off and I cannot name it.")
    assert ru.intent == "clarify"
    assert en.intent == "clarify"
    assert ru.confidence >= 0.6
    assert en.confidence >= 0.6


@pytest.mark.asyncio
async def test_defensive_cases_detect_defensive_and_clarify() -> None:
    agent = StateAnalyzerAgent(client=None, model="gpt-5-nano")
    agent._get_client = lambda: None  # type: ignore[method-assign]
    ru = await agent.analyze("Может это не поможет, но объясни почему я так реагирую.")
    en = await agent.analyze("Maybe this will not help, but explain why I react like this.")
    assert ru.openness == "defensive"
    assert en.openness == "defensive"
    assert ru.intent == "clarify"
    assert en.intent == "clarify"


@pytest.mark.asyncio
async def test_deterministic_debug_contains_compact_payload_without_raw_user_text() -> None:
    agent = StateAnalyzerAgent(client=None, model="gpt-5-nano")
    agent._get_client = lambda: None  # type: ignore[method-assign]
    _ = await agent.analyze("Maybe this will not help, but explain why I react like this.")
    debug = agent.last_debug
    assert debug.get("model") == "deterministic"
    assert debug.get("api_mode") == "heuristic"
    assert "deterministic" in debug
    deterministic = debug.get("deterministic") or {}
    assert deterministic.get("intent") == "clarify"
    # Ensure compact debug contains no raw user text fields.
    assert "user_message" not in deterministic
