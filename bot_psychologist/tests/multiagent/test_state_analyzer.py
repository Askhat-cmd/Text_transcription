from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import state_analyzer_agent
from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent
from bot_agent.multiagent.agents.thread_manager import ThreadManagerAgent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
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
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))]
        )


class _FakeClient:
    def __init__(self, payload: str, should_fail: bool = False) -> None:
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(payload=payload, should_fail=should_fail)
        )


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
async def test_sa_01_safety_ru() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("не могу больше, хочу умереть")
    assert snapshot.safety_flag is True
    assert snapshot.nervous_state == "hyper"


@pytest.mark.asyncio
async def test_sa_02_safety_en() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("I want to kill myself")
    assert snapshot.safety_flag is True
    assert snapshot.nervous_state == "hyper"


@pytest.mark.asyncio
async def test_sa_03_safety_override_mode_with_thread_manager() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    manager = ThreadManagerAgent()
    snapshot = await agent.analyze("не могу больше, хочу умереть")
    updated = await manager.update(
        user_message="не могу больше, хочу умереть",
        state_snapshot=snapshot,
        user_id="u1",
        current_thread=_thread(),
        archived_threads=[],
    )
    assert updated.response_mode == "safe_override"


@pytest.mark.asyncio
async def test_sa_04_safety_no_llm_call() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    _ = await agent.analyze("лучше бы меня не было")
    assert len(client.chat.completions.calls) == 0


@pytest.mark.asyncio
async def test_sa_05_hyper_keywords() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("паника, не могу успокоиться")
    assert snapshot.nervous_state == "hyper"


@pytest.mark.asyncio
async def test_sa_06_hypo_keywords() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("ничего не чувствую, пустота")
    assert snapshot.nervous_state == "hypo"


@pytest.mark.asyncio
async def test_sa_07_caps_hyper() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("МНЕ ОЧЕНЬ ПЛОХО!!!")
    assert snapshot.nervous_state == "hyper"


@pytest.mark.asyncio
async def test_sa_08_short_hypo_or_window() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("не знаю")
    assert snapshot.nervous_state in {"hypo", "window"}


@pytest.mark.asyncio
async def test_sa_09_contact_intent() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("просто хочу поговорить, не надо советов")
    assert snapshot.intent == "contact"


@pytest.mark.asyncio
async def test_sa_10_solution_intent() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("что мне делать с этим, дай совет")
    assert snapshot.intent == "solution"


@pytest.mark.asyncio
async def test_sa_11_vent_intent() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("я злюсь, это несправедливо")
    assert snapshot.intent == "vent"


@pytest.mark.asyncio
async def test_sa_12_defensive_openness() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("все равно не поможет, уже пробовал")
    assert snapshot.openness == "defensive"


@pytest.mark.asyncio
async def test_sa_13_start_command_snapshot() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("/start")
    assert snapshot.intent == "contact"
    assert snapshot.confidence == pytest.approx(0.9, abs=1e-6)


@pytest.mark.asyncio
async def test_sa_14_empty_message_snapshot() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    snapshot = await agent.analyze("  ")
    assert snapshot.nervous_state == "window"
    assert snapshot.confidence == pytest.approx(0.5, abs=1e-6)


@pytest.mark.asyncio
async def test_sa_15_llm_called_when_ambiguous() -> None:
    client = _FakeClient(_llm_payload(intent="clarify"))
    agent = StateAnalyzerAgent(client=client)
    _ = await agent.analyze("ну не знаю что сказать")
    assert len(client.chat.completions.calls) == 1


@pytest.mark.asyncio
async def test_sa_16_llm_not_called_when_certain() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    _ = await agent.analyze("просто хочу поговорить, не надо советов, да, понимаю")
    assert len(client.chat.completions.calls) == 0


@pytest.mark.asyncio
async def test_sa_17_llm_fallback_on_error() -> None:
    client = _FakeClient(_llm_payload(), should_fail=True)
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("хм...")
    assert snapshot.confidence <= 0.6
    assert snapshot.safety_flag is False


@pytest.mark.asyncio
async def test_sa_18_confidence_in_range() -> None:
    client = _FakeClient(_llm_payload(confidence=2.0))
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("ну наверное")
    assert 0.0 <= snapshot.confidence <= 1.0


@pytest.mark.asyncio
async def test_sa_19_all_fields_present() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("неоднозначно")
    payload = snapshot.to_dict()
    assert set(payload.keys()) == {
        "nervous_state",
        "intent",
        "openness",
        "ok_position",
        "safety_flag",
        "confidence",
    }


@pytest.mark.asyncio
async def test_sa_20_valid_nervous_values() -> None:
    client = _FakeClient(_llm_payload(nervous_state="INVALID"))
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("что-то странно")
    assert snapshot.nervous_state in {"window", "hyper", "hypo"}


@pytest.mark.asyncio
async def test_sa_21_valid_intent_values() -> None:
    client = _FakeClient(_llm_payload(intent="INVALID"))
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("что-то странно")
    assert snapshot.intent in {"clarify", "vent", "explore", "contact", "solution"}


@pytest.mark.asyncio
async def test_sa_22_valid_openness_values() -> None:
    client = _FakeClient(_llm_payload(openness="INVALID"))
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("что-то странно")
    assert snapshot.openness in {"open", "mixed", "defensive", "collapsed"}


@pytest.mark.asyncio
async def test_sa_23_valid_ok_position_values() -> None:
    client = _FakeClient(_llm_payload(ok_position="INVALID"))
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("что-то странно")
    assert snapshot.ok_position in {"I+W+", "I-W+", "I+W-", "I-W-"}


@pytest.mark.asyncio
async def test_sa_24_previous_thread_context_in_prompt() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    prev = _thread("u2")
    _ = await agent.analyze("ну не знаю", previous_thread=prev)
    prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "тревога перед встречей" in prompt


@pytest.mark.asyncio
async def test_sa_25_long_message_truncated() -> None:
    client = _FakeClient(_llm_payload())
    agent = StateAnalyzerAgent(client=client)
    long_message = "а" * 1500
    _ = await agent.analyze(long_message)
    prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert "а" * 1000 in prompt
    assert "а" * 1200 not in prompt


def test_sa_26_analyze_is_coroutine() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
    assert asyncio.iscoroutinefunction(agent.analyze)


def test_sa_27_singleton_export_exists() -> None:
    assert state_analyzer_agent is not None
    assert isinstance(state_analyzer_agent, StateAnalyzerAgent)


def test_sa_28_model_from_agent_llm_config() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import (
        reset_model_for_agent,
        set_model_for_agent,
    )

    set_model_for_agent("state_analyzer", "gpt-5-mini")
    try:
        agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload()))
        assert agent._model == "gpt-5-mini"
    finally:
        reset_model_for_agent("state_analyzer")


@pytest.mark.asyncio
async def test_sa_29_fixtures_pass() -> None:
    fixtures_path = Path(__file__).parent / "fixtures" / "state_analyzer_fixtures.json"
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    agent = StateAnalyzerAgent(client=_FakeClient(_llm_payload(intent="clarify")))
    for item in payload:
        snapshot = await agent.analyze(item["message"])
        expected = item["expected"]
        for key, expected_value in expected.items():
            if key == "confidence":
                assert snapshot.confidence == pytest.approx(float(expected_value), abs=1e-3)
            else:
                assert getattr(snapshot, key) == expected_value


@pytest.mark.asyncio
async def test_sa_30_integration_with_thread_manager() -> None:
    analyzer = StateAnalyzerAgent(client=_FakeClient(_llm_payload(intent="clarify")))
    snapshot = await analyzer.analyze("хочу разобраться, что со мной")
    manager = ThreadManagerAgent()
    updated = await manager.update(
        user_message="хочу разобраться, что со мной",
        state_snapshot=snapshot,
        user_id="u30",
        current_thread=None,
        archived_threads=[],
    )
    assert isinstance(snapshot, StateSnapshot)
    assert updated.user_id == "u30"
