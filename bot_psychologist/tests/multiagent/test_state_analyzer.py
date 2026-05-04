from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import state_analyzer_agent
from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent
from bot_agent.multiagent.contracts.thread_state import ThreadState


class _FakeCompletions:
    def __init__(self, payload: str, should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=50, completion_tokens=25, total_tokens=75),
        )


class _FakeResponses:
    def __init__(self, payload: str, should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=40, output_tokens=20, total_tokens=60),
        )


class _FakeClient:
    def __init__(self, payload: str, should_fail: bool = False) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload, should_fail=should_fail))
        self.responses = _FakeResponses(payload=payload, should_fail=should_fail)


def _thread(user_id: str = "u1") -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id=user_id,
        core_direction="тревога перед встречей",
        phase="clarify",
        open_loops=["что со мной"],
        closed_loops=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _llm_payload(
    *,
    nervous_state: str = "window",
    intent: str = "explore",
    openness: str = "mixed",
    ok_position: str = "I+W+",
    confidence: float = 0.77,
) -> str:
    return json.dumps(
        {
            "nervous_state": nervous_state,
            "intent": intent,
            "openness": openness,
            "ok_position": ok_position,
            "confidence": confidence,
        }
    )


@pytest.mark.asyncio
async def test_safety_keywords_skip_llm_call() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client, model="gpt-5-nano")
    snapshot = await agent.analyze("не могу больше, хочу умереть")
    assert snapshot.safety_flag is True
    assert len(client.responses.calls) == 0
    assert len(client.chat.completions.calls) == 0


@pytest.mark.asyncio
async def test_ambiguous_message_gpt5_uses_responses() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client, model="gpt-5-nano")
    snapshot = await agent.analyze("ну не знаю что сказать")

    assert snapshot.intent in {"clarify", "explore", "contact", "solution", "vent"}
    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 0
    req = client.responses.calls[0]
    assert req["model"] == "gpt-5-nano"
    assert req["max_output_tokens"] == 240
    assert "temperature" not in req
    assert "max_tokens" not in req
    assert agent.last_debug["api_mode"] == "responses"


@pytest.mark.asyncio
async def test_ambiguous_message_gpt4o_uses_chat() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client, model="gpt-4o-mini")
    await agent.analyze("ну не знаю что сказать")

    assert len(client.chat.completions.calls) == 1
    assert len(client.responses.calls) == 0
    req = client.chat.completions.calls[0]
    assert req["model"] == "gpt-4o-mini"
    assert req["max_tokens"] == 240
    assert req["response_format"] == {"type": "json_object"}
    assert req["temperature"] == pytest.approx(0.1, abs=1e-9)
    assert agent.last_debug["api_mode"] == "chat_completions"


@pytest.mark.asyncio
async def test_state_analyzer_hot_swap_model_without_restart() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client)

    set_model_for_agent("state_analyzer", "gpt-5-nano")
    await agent.analyze("неоднозначный вопрос")
    assert agent.last_debug["api_mode"] == "responses"

    set_model_for_agent("state_analyzer", "gpt-4o-mini")
    await agent.analyze("неоднозначный вопрос")
    assert agent.last_debug["api_mode"] == "chat_completions"

    reset_model_for_agent("state_analyzer")


@pytest.mark.asyncio
async def test_state_analyzer_error_written_to_debug() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"), should_fail=True)
    agent = StateAnalyzerAgent(client=client, model="gpt-5-nano")
    snapshot = await agent.analyze("неоднозначный вопрос")

    assert snapshot.safety_flag is False
    assert agent.last_debug.get("error")


@pytest.mark.asyncio
async def test_previous_thread_context_in_prompt_for_responses() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client, model="gpt-5-nano")
    prev = _thread("u2")
    await agent.analyze("ну не знаю", previous_thread=prev)

    input_payload = str(client.responses.calls[0]["input"])
    assert "тревога перед встречей" in input_payload


@pytest.mark.asyncio
async def test_long_message_truncated_in_prompt() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client, model="gpt-5-nano")
    long_message = "а" * 1500
    await agent.analyze(long_message)

    input_payload = str(client.responses.calls[0]["input"])
    assert "а" * 1000 in input_payload
    assert "а" * 1200 not in input_payload


def test_singleton_export_exists() -> None:
    assert state_analyzer_agent is not None
    assert isinstance(state_analyzer_agent, StateAnalyzerAgent)


def test_model_from_agent_llm_config_dynamic() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    set_model_for_agent("state_analyzer", "gpt-5-mini")
    try:
        agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
        assert agent._resolve_model() == "gpt-5-mini"
    finally:
        reset_model_for_agent("state_analyzer")
