from __future__ import annotations

import json
import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.state_analyzer import StateAnalyzerAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


class _QueueCompletions:
    def __init__(self, payloads: list[str]) -> None:
        self._payloads = payloads
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        idx = min(len(self.calls) - 1, len(self._payloads) - 1)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._payloads[idx]))]
        )


class _QueueResponses:
    def __init__(self, payloads: list[str]) -> None:
        self._payloads = payloads
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        idx = min(len(self.calls) - 1, len(self._payloads) - 1)
        return SimpleNamespace(
            output_text=self._payloads[idx],
            usage=SimpleNamespace(input_tokens=12, output_tokens=7, total_tokens=19),
        )


class _FakeClient:
    def __init__(self, payloads: list[str]) -> None:
        self.chat = SimpleNamespace(completions=_QueueCompletions(payloads))
        self.responses = _QueueResponses(payloads)


def _analysis_payload(
    *,
    nervous_state: str = "window",
    intent: str = "explore",
    openness: str = "mixed",
    ok_position: str = "I+W+",
    confidence: float = 0.79,
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


def _thread(*, response_mode: str = "reflect") -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="th-safe-1",
        user_id="u-safe",
        core_direction="safe-test",
        phase="clarify",
        response_mode=response_mode,  # type: ignore[arg-type]
        created_at=now,
        updated_at=now,
    )


def test_sd_01_explicit_keyword_direct() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient([_analysis_payload()]))
    assert agent._detect_safety("\u043b\u0443\u0447\u0448\u0435 \u0431\u044b \u043c\u0435\u043d\u044f \u043d\u0435 \u0431\u044b\u043b\u043e") is True


def test_sd_02_euphemism_tired_of_life() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient([_analysis_payload()]))
    assert (
        agent._detect_safety(
            "\u043f\u0440\u043e\u0441\u0442\u043e \u0443\u0441\u0442\u0430\u043b\u0430 \u043e\u0442 \u0436\u0438\u0437\u043d\u0438, \u0432\u0441\u0435 \u043d\u0430\u0434\u043e\u0435\u043b\u043e"
        )
        is True
    )


def test_sd_03_euphemism_disappear() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient([_analysis_payload()]))
    assert (
        agent._detect_safety(
            "\u0445\u043e\u0447\u0443 \u043f\u0440\u043e\u0441\u0442\u043e \u0438\u0441\u0447\u0435\u0437\u043d\u0443\u0442\u044c \u0438 \u043d\u0438\u043a\u043e\u0433\u043e \u043d\u0435 \u0432\u0438\u0434\u0435\u0442\u044c"
        )
        is True
    )


@pytest.mark.asyncio
async def test_sd_04_llm_fallback_for_implicit_crisis() -> None:
    client = _FakeClient(
        [
            _analysis_payload(openness="collapsed", ok_position="I-W-", confidence=0.83),
            "YES",
        ]
    )
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("\u044f \u043d\u0435 \u0432\u0438\u0436\u0443 \u0432\u044b\u0445\u043e\u0434\u0430")
    assert snapshot.safety_flag is True


def test_sd_05_false_positive_check() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient([_analysis_payload()]))
    assert (
        agent._detect_safety(
            "\u043c\u043d\u0435 \u043f\u043b\u043e\u0445\u043e \u043d\u043e \u044f \u0441\u043f\u0440\u0430\u0432\u043b\u044e\u0441\u044c"
        )
        is False
    )


def test_sd_06_false_positive_tired_from_work() -> None:
    agent = StateAnalyzerAgent(client=_FakeClient([_analysis_payload()]))
    assert (
        agent._detect_safety(
            "\u0443\u0441\u0442\u0430\u043b\u0430 \u043e\u0442 \u0440\u0430\u0431\u043e\u0442\u044b, \u0445\u043e\u0447\u0443 \u043e\u0442\u0434\u043e\u0445\u043d\u0443\u0442\u044c"
        )
        is False
    )


@pytest.mark.asyncio
async def test_sd_07_safe_override_mode_activated(monkeypatch: pytest.MonkeyPatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="hyper",
                intent="contact",
                openness="collapsed",
                ok_position="I-W-",
                safety_flag=True,
                confidence=0.99,
            )
        ),
    )
    monkeypatch.setattr(
        orch_module.thread_manager_agent,
        "update",
        AsyncMock(return_value=_thread(response_mode="safe_override")),
    )
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle()),
    )
    monkeypatch.setattr(
        orch_module.writer_agent,
        "write",
        AsyncMock(return_value="safe"),
    )
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda *_args, **_kwargs: ValidationResult(is_blocked=False),
    )
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.thread_storage, "archive_thread", lambda *_a, **_k: None)
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "update",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        orch_module.asyncio,
        "create_task",
        lambda coro: (coro.close(), None)[1],
    )

    result = await MultiAgentOrchestrator().run(query="\u043f\u043b\u043e\u0445\u043e", user_id="u-safe")
    assert result["response_mode"] == "safe_override"


def test_sd_08_encoding_normalize_cyrillic() -> None:
    orchestrator = MultiAgentOrchestrator()
    query = "\u043f\u0440\u0438\u0432\u0435\u0442, \u043a\u0430\u043a \u0434\u0435\u043b\u0430?"
    assert orchestrator._normalize_query(query) == query


def test_sd_09_encoding_normalize_mojibake() -> None:
    orchestrator = MultiAgentOrchestrator()
    original = "\u043f\u0440\u0438\u0432\u0435\u0442"
    mojibake = original.encode("utf-8").decode("cp1251")
    assert orchestrator._normalize_query(mojibake) == original


@pytest.mark.asyncio
async def test_sd_10_safety_snapshot_fields() -> None:
    client = _FakeClient(
        [
            _analysis_payload(openness="collapsed", ok_position="I-W-", confidence=0.8),
            "YES",
        ]
    )
    agent = StateAnalyzerAgent(client=client)
    snapshot = await agent.analyze("\u044f \u0432 \u043f\u043e\u043b\u043d\u043e\u043c \u0442\u0443\u043f\u0438\u043a\u0435")
    assert snapshot.safety_flag is True
    assert snapshot.nervous_state == "hyper"
    assert snapshot.openness == "collapsed"
    assert snapshot.ok_position == "I-W-"
