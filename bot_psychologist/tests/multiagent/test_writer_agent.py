from __future__ import annotations

import importlib
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


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
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))]
        )


class _FakeClient:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(payload=payload, should_fail=should_fail)
        )


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
async def test_wa_01_write_returns_string() -> None:
    agent = WriterAgent(client=_FakeClient("тест"))
    result = await agent.write(_contract())
    assert isinstance(result, str)
    assert result.strip() != ""


@pytest.mark.asyncio
async def test_wa_02_write_non_empty_mock() -> None:
    agent = WriterAgent(client=_FakeClient("готовый ответ"))
    result = await agent.write(_contract())
    assert result == "готовый ответ"


@pytest.mark.asyncio
async def test_wa_03_safety_fallback_empty_llm() -> None:
    agent = WriterAgent(client=_FakeClient(""))
    result = await agent.write(_contract(mode="safe_override", safety_active=True))
    assert "здесь" in result.lower()
    assert "один" in result.lower()


@pytest.mark.asyncio
async def test_wa_04_safety_fallback_llm_error() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True))
    result = await agent.write(_contract(mode="safe_override", safety_active=True))
    assert "здесь" in result.lower()


@pytest.mark.asyncio
async def test_wa_05_safety_fallback_ru() -> None:
    agent = WriterAgent(client=_FakeClient(""))
    result = await agent.write(
        _contract(mode="safe_override", safety_active=True, message="мне тяжело")
    )
    assert "вдох" in result.lower() or "здесь" in result.lower()


@pytest.mark.asyncio
async def test_wa_06_safety_fallback_en() -> None:
    agent = WriterAgent(client=_FakeClient(""))
    result = await agent.write(
        _contract(mode="safe_override", safety_active=True, message="I feel overwhelmed")
    )
    assert "i'm here" in result.lower() or "you're not alone" in result.lower()


@pytest.mark.asyncio
async def test_wa_07_static_fallback_validate() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True))
    result = await agent.write(_contract(mode="validate", safety_active=False))
    assert "слышу" in result.lower()


@pytest.mark.asyncio
async def test_wa_08_static_fallback_regulate() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True))
    result = await agent.write(_contract(mode="regulate", safety_active=False))
    assert "вдох" in result.lower()


@pytest.mark.asyncio
async def test_wa_09_static_fallback_safe() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True))
    result = await agent.write(_contract(mode="safe_override", safety_active=False))
    assert "слышу" in result.lower() or "здесь" in result.lower()


def test_wa_10_writer_contract_fields() -> None:
    contract = _contract()
    assert hasattr(contract, "user_message")
    assert hasattr(contract, "thread_state")
    assert hasattr(contract, "memory_bundle")
    assert hasattr(contract, "response_language")


def test_wa_11_to_prompt_context_keys() -> None:
    ctx = _contract().to_prompt_context()
    expected = {
        "user_message",
        "phase",
        "response_mode",
        "response_goal",
        "must_avoid",
        "ok_position",
        "openness",
        "open_loops",
        "closed_loops",
        "core_direction",
        "nervous_state",
        "safety_active",
        "conversation_context",
        "user_profile_patterns",
        "user_profile_values",
        "semantic_hits",
        "has_relevant_knowledge",
    }
    assert expected.issubset(set(ctx.keys()))


@pytest.mark.asyncio
async def test_wa_12_must_avoid_in_prompt() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client)
    contract = _contract(must_avoid=["оценка", "диагноз"])
    await agent._call_llm(contract)
    user_prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "оценка" in user_prompt
    assert "диагноз" in user_prompt


@pytest.mark.asyncio
async def test_wa_13_open_loops_in_prompt() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client)
    contract = _contract(open_loops=["почему я так реагирую"])
    await agent._call_llm(contract)
    user_prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "почему я так реагирую" in user_prompt


@pytest.mark.asyncio
async def test_wa_14_conv_context_truncated() -> None:
    long_ctx = "x" * 2600
    client = _FakeClient("ok")
    agent = WriterAgent(client=client)
    await agent._call_llm(_contract(conversation_context=long_ctx))
    user_prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "x" * 2000 in user_prompt
    assert "x" * 2200 not in user_prompt


@pytest.mark.asyncio
async def test_wa_15_semantic_hits_limit() -> None:
    hits = [
        SemanticHit(chunk_id="1", content="hit_1", source="s", score=0.9),
        SemanticHit(chunk_id="2", content="hit_2", source="s", score=0.8),
        SemanticHit(chunk_id="3", content="hit_3", source="s", score=0.7),
    ]
    client = _FakeClient("ok")
    agent = WriterAgent(client=client)
    await agent._call_llm(_contract(hits=hits))
    user_prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "hit_1" in user_prompt
    assert "hit_2" in user_prompt
    assert "hit_3" not in user_prompt


def test_wa_16_model_from_agent_llm_config() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import (
        reset_model_for_agent,
        set_model_for_agent,
    )

    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    set_model_for_agent("writer", "gpt-4.1-mini")
    try:
        agent = writer_module.WriterAgent(client=_FakeClient("ok"))
        assert agent._model == "gpt-4.1-mini"
    finally:
        reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_wa_17_temperature_07(monkeypatch) -> None:
    def _value(name: str, default: str = "") -> str:
        if name == "WRITER_MODEL":
            return "gpt-5-mini"
        if name == "WRITER_MAX_TOKENS":
            return "400"
        if name == "WRITER_TEMPERATURE":
            return "0.7"
        return default

    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    monkeypatch.setattr(writer_module.feature_flags, "value", _value)
    client = _FakeClient("ok")
    agent = writer_module.WriterAgent(client=client)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[0]["temperature"] == pytest.approx(0.7, abs=1e-9)


@pytest.mark.asyncio
async def test_wa_18_max_tokens_400(monkeypatch) -> None:
    def _value(name: str, default: str = "") -> str:
        if name == "WRITER_MODEL":
            return "gpt-5-mini"
        if name == "WRITER_MAX_TOKENS":
            return "400"
        if name == "WRITER_TEMPERATURE":
            return "0.7"
        return default

    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    monkeypatch.setattr(writer_module.feature_flags, "value", _value)
    client = _FakeClient("ok")
    agent = writer_module.WriterAgent(client=client)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[0]["max_tokens"] == 400


def test_wa_19_async_method() -> None:
    assert inspect.iscoroutinefunction(WriterAgent.write)


@pytest.mark.asyncio
async def test_wa_20_no_client_fallback(monkeypatch) -> None:
    agent = WriterAgent(client=None)
    monkeypatch.setattr(agent, "_get_client", lambda: None)
    result = await agent.write(_contract(mode="validate"))
    assert result.strip() != ""


def test_wa_21_detect_lang_ru() -> None:
    assert WriterAgent._detect_language("Привет, как ты?") == "ru"


def test_wa_22_detect_lang_en() -> None:
    assert WriterAgent._detect_language("Hello there, how are you?") == "en"


@pytest.mark.asyncio
async def test_wa_23_orchestrator_calls_writer(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6)),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    writer_mock = AsyncMock(return_value="writer answer")
    monkeypatch.setattr(orch_module.writer_agent, "write", writer_mock)
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)

    def _consume_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(orch_module.asyncio, "create_task", _consume_task)
    orchestrator = MultiAgentOrchestrator()
    _ = await orchestrator.run(query="привет", user_id="u1")
    assert writer_mock.await_count == 1


@pytest.mark.asyncio
async def test_wa_24_orchestrator_answer_in_result(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6)),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.writer_agent, "write", AsyncMock(return_value="neo answer"))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)

    def _consume_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(orch_module.asyncio, "create_task", _consume_task)
    orchestrator = MultiAgentOrchestrator()
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["answer"] == "neo answer"


def test_wa_25_orchestrator_no_build_answer() -> None:
    assert not hasattr(MultiAgentOrchestrator, "_build_answer")


@pytest.mark.asyncio
async def test_wa_26_fixture_f01() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "writer_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(x for x in payload if x["id"] == "WA-F01")
    agent = WriterAgent(client=_FakeClient(item["llm_mock_response"]))
    result = await agent.write(
        _contract(mode=item["response_mode"], safety_active=item["safety_active"])
    )
    assert result.strip() != ""


@pytest.mark.asyncio
async def test_wa_27_fixture_f02() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "writer_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(x for x in payload if x["id"] == "WA-F02")
    agent = WriterAgent(client=_FakeClient(item["llm_mock_response"]))
    result = await agent.write(
        _contract(
            mode=item["response_mode"],
            safety_active=item["safety_active"],
            must_avoid=item["must_avoid"],
        )
    )
    assert result == item["llm_mock_response"]


@pytest.mark.asyncio
async def test_wa_28_fixture_f03() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "writer_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(x for x in payload if x["id"] == "WA-F03")
    agent = WriterAgent(client=_FakeClient(item["llm_mock_response"]))
    result = await agent.write(
        _contract(mode=item["response_mode"], safety_active=item["safety_active"])
    )
    for token in item["expected_contains"]:
        assert token in result.lower()


@pytest.mark.asyncio
async def test_wa_29_fixture_f04() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "writer_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(x for x in payload if x["id"] == "WA-F04")
    agent = WriterAgent(client=_FakeClient(item["llm_mock_response"]))
    result = await agent.write(
        _contract(mode=item["response_mode"], safety_active=item["safety_active"])
    )
    assert result == item["llm_mock_response"]


@pytest.mark.asyncio
async def test_wa_30_fixture_f05() -> None:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "writer_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    item = next(x for x in payload if x["id"] == "WA-F05")
    agent = WriterAgent(client=_FakeClient("x", should_fail=item["llm_throws"]))
    result = await agent.write(
        _contract(mode=item["response_mode"], safety_active=item["safety_active"])
    )
    for token in item["expected_contains"]:
        assert token in result.lower()
