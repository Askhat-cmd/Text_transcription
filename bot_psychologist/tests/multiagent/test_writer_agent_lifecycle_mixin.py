from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent_lifecycle_mixin import WriterAgentLifecycleMixin


class _ProbeLifecycleAgent(WriterAgentLifecycleMixin):
    def __init__(
        self,
        *,
        llm_result: str | None = None,
        llm_error: Exception | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._llm_result = llm_result
        self._llm_error = llm_error
        self._model = model
        self.last_debug: dict[str, object] = {}

    def _resolve_model(self) -> str:
        return self._model

    @staticmethod
    def _get_temperature_for_agent(agent_name: str) -> float:
        assert agent_name == "writer"
        return 0.7

    async def _call_llm(
        self,
        contract: object,
        *,
        prompt_constraint_decision: dict[str, object] | None = None,
    ) -> str:
        if self._llm_error is not None:
            raise self._llm_error
        return self._llm_result or ""

    def _enforce_answer_compliance(self, result: str, contract: object) -> str:
        return result

    def _apply_name_continuity(self, result: str, contract: object) -> str:
        return result

    @staticmethod
    def _static_fallback(contract: object) -> str:
        return "STATIC_FALLBACK"

    @staticmethod
    def _detect_language(text: str) -> str:
        return "ru"


def _contract(*, safety_active: bool, profile: str = "safe_guided") -> object:
    return SimpleNamespace(
        user_message="Мне сейчас тяжело, ответь спокойно.",
        response_language=None,
        dialogue_policy={"profile": profile},
        thread_state=SimpleNamespace(safety_active=safety_active),
    )


def test_resolve_runtime_settings_preserves_profile_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot_agent.multiagent.agents import writer_agent_lifecycle_mixin as lifecycle_module

    def _fake_value(name: str, default: str | None = None) -> str | None:
        mapping = {
            "MULTIAGENT_MAX_TOKENS": "200",
            "WRITER_MAX_TOKENS": "180",
            "MULTIAGENT_LLM_TIMEOUT": "12.5",
        }
        return mapping.get(name, default)

    monkeypatch.setattr(lifecycle_module.feature_flags, "value", _fake_value)
    monkeypatch.setattr(_ProbeLifecycleAgent, "_get_temperature_for_agent", staticmethod(lambda agent_name: 0.55))

    agent = _ProbeLifecycleAgent(model="gpt-4o-mini")
    safe_settings = agent._resolve_runtime_settings("safe_guided")
    mvp_settings = agent._resolve_runtime_settings("mvp_free_dialogue")

    assert safe_settings == {
        "model": "gpt-4o-mini",
        "timeout": 12.5,
        "max_tokens": 200,
        "temperature": 0.55,
    }
    assert mvp_settings == {
        "model": "gpt-4o-mini",
        "timeout": 12.5,
        "max_tokens": 2500,
        "temperature": 0.55,
    }


@pytest.mark.asyncio
async def test_write_safety_success_returns_llm_text_without_fallback() -> None:
    agent = _ProbeLifecycleAgent(llm_result="SAFE_OK")
    result = await agent.write(_contract(safety_active=True))

    assert result == "SAFE_OK"
    assert agent.last_debug["fallback_used"] is False
    assert agent.last_debug["error"] is None


@pytest.mark.asyncio
async def test_write_safety_exception_returns_safe_override_and_sets_debug() -> None:
    agent = _ProbeLifecycleAgent(llm_error=RuntimeError("SAFE_BOOM"))
    result = await agent.write(_contract(safety_active=True))

    assert result == "Я здесь. Ты не один. Сделай медленный вдох — я рядом."
    assert agent.last_debug["fallback_used"] is True
    assert agent.last_debug["error"] == "SAFE_BOOM"


@pytest.mark.asyncio
async def test_write_normal_empty_returns_static_fallback() -> None:
    agent = _ProbeLifecycleAgent(llm_result="   ")
    result = await agent.write(_contract(safety_active=False))

    assert result == "STATIC_FALLBACK"
    assert agent.last_debug["fallback_used"] is True
    assert agent.last_debug["error"] is None


@pytest.mark.asyncio
async def test_write_normal_exception_returns_static_fallback_and_sets_debug() -> None:
    agent = _ProbeLifecycleAgent(llm_error=RuntimeError("NORMAL_BOOM"))
    result = await agent.write(_contract(safety_active=False))

    assert result == "STATIC_FALLBACK"
    assert agent.last_debug["fallback_used"] is True
    assert agent.last_debug["error"] == "NORMAL_BOOM"
