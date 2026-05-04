from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeCompletions:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=30, total_tokens=130),
        )


class _FakeResponses:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=90, output_tokens=40, total_tokens=130),
        )


class _FakeClient:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload, should_fail=should_fail))
        self.responses = _FakeResponses(payload=payload, should_fail=should_fail)


def _thread(
    *,
    mode: str = "reflect",
    safety_active: bool = False,
    must_avoid: list[str] | None = None,
    open_loops: list[str] | None = None,
) -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id="u1",
        core_direction="тревога перед встречей",
        phase="clarify",
        response_mode=mode,  # type: ignore[arg-type]
        response_goal="поддержка",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        must_avoid=list(must_avoid or []),
        open_loops=list(open_loops or []),
        safety_active=safety_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract(
    *,
    mode: str = "reflect",
    safety_active: bool = False,
    message: str = "привет",
    must_avoid: list[str] | None = None,
    open_loops: list[str] | None = None,
    conversation_context: str = "u: hi\na: hello",
    hits: list[SemanticHit] | None = None,
) -> WriterContract:
    bundle = MemoryBundle(
        conversation_context=conversation_context,
        user_profile=UserProfile(patterns=["avoidance"], values=["honesty"]),
        semantic_hits=list(hits or []),
        has_relevant_knowledge=bool(hits),
        context_turns=3,
    )
    return WriterContract(
        user_message=message,
        thread_state=_thread(
            mode=mode,
            safety_active=safety_active,
            must_avoid=must_avoid,
            open_loops=open_loops,
        ),
        memory_bundle=bundle,
    )


@pytest.mark.asyncio
async def test_write_returns_non_empty() -> None:
    agent = WriterAgent(client=_FakeClient("готовый ответ"), model="gpt-5-mini")
    result = await agent.write(_contract())
    assert isinstance(result, str)
    assert result.strip() != ""


@pytest.mark.asyncio
async def test_safety_fallback_on_error_sets_debug() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True), model="gpt-5-mini")
    result = await agent.write(_contract(mode="safe_override", safety_active=True))
    assert "здесь" in result.lower()
    assert agent.last_debug.get("error")
    assert agent.last_debug.get("fallback_used") is True


@pytest.mark.asyncio
async def test_static_fallback_validate_on_error() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True), model="gpt-5-mini")
    result = await agent.write(_contract(mode="validate", safety_active=False))
    assert "слышу" in result.lower()
    assert agent.last_debug.get("fallback_used") is True


@pytest.mark.asyncio
async def test_writer_gpt5_uses_responses_api() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())

    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 0
    req = client.responses.calls[0]
    assert req["model"] == "gpt-5-mini"
    assert req["max_output_tokens"] == 600
    assert "temperature" not in req
    assert "max_tokens" not in req
    assert agent.last_debug["api_mode"] == "responses"


@pytest.mark.asyncio
async def test_writer_gpt4o_uses_chat_api_with_temperature() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-4o-mini")
    await agent._call_llm(_contract())

    assert len(client.chat.completions.calls) == 1
    assert len(client.responses.calls) == 0
    req = client.chat.completions.calls[0]
    assert req["model"] == "gpt-4o-mini"
    assert req["temperature"] == pytest.approx(0.7, abs=1e-9)
    assert req["max_tokens"] == 600
    assert agent.last_debug["api_mode"] == "chat_completions"


@pytest.mark.asyncio
async def test_prompt_contains_must_avoid_for_responses_path() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(must_avoid=["оценка", "диагноз"]))

    user_input = str(client.responses.calls[0]["input"])
    assert "оценка" in user_input
    assert "диагноз" in user_input


@pytest.mark.asyncio
async def test_prompt_contains_open_loops_for_responses_path() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(open_loops=["почему я так реагирую"]))

    user_input = str(client.responses.calls[0]["input"])
    assert "почему я так реагирую" in user_input


@pytest.mark.asyncio
async def test_conversation_context_truncated() -> None:
    long_ctx = "x" * 2600
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(conversation_context=long_ctx))

    user_input = str(client.responses.calls[0]["input"])
    assert "x" * 2000 in user_input
    assert "x" * 2200 not in user_input


@pytest.mark.asyncio
async def test_semantic_hits_limit_to_two() -> None:
    hits = [
        SemanticHit(chunk_id="1", content="hit_1", source="s", score=0.9),
        SemanticHit(chunk_id="2", content="hit_2", source="s", score=0.8),
        SemanticHit(chunk_id="3", content="hit_3", source="s", score=0.7),
    ]
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(hits=hits))

    user_input = str(client.responses.calls[0]["input"])
    assert "hit_1" in user_input
    assert "hit_2" in user_input
    assert "hit_3" not in user_input


def test_model_from_agent_llm_config_dynamic() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    set_model_for_agent("writer", "gpt-4.1-mini")
    try:
        agent = writer_module.WriterAgent(client=_FakeClient("ok"))
        assert agent._resolve_model() == "gpt-4.1-mini"
    finally:
        reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_hot_swap_model_without_recreate_instance() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    client = _FakeClient("ok")
    agent = WriterAgent(client=client)

    set_model_for_agent("writer", "gpt-5-mini")
    await agent._call_llm(_contract())
    assert agent.last_debug["api_mode"] == "responses"

    set_model_for_agent("writer", "gpt-4o-mini")
    await agent._call_llm(_contract())
    assert agent.last_debug["api_mode"] == "chat_completions"

    reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_hot_swap_temperature_without_recreate_instance() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import (
        reset_temperature_for_agent,
        set_temperature_for_agent,
    )

    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-4o-mini")

    set_temperature_for_agent("writer", 0.33)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[-1]["temperature"] == pytest.approx(0.33, abs=1e-9)

    set_temperature_for_agent("writer", 1.1)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[-1]["temperature"] == pytest.approx(1.1, abs=1e-9)

    reset_temperature_for_agent("writer")


def test_detect_language_ru() -> None:
    assert WriterAgent._detect_language("Привет, как ты?") == "ru"


def test_detect_language_en() -> None:
    assert WriterAgent._detect_language("Hello there, how are you?") == "en"
