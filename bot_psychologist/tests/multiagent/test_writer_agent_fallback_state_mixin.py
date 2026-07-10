from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent_fallback_helpers import (
    _build_no_practice_fallback_text,
    _normalize_name,
    _strip_optional_followup_invitation,
)
from bot_agent.multiagent.agents.writer_agent_fallback_state_mixin import (
    WriterAgentFallbackStateMixin,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _ProbeAgent(WriterAgentFallbackStateMixin):
    _PRACTICE_MARKERS = (
        "практик",
        "упражн",
        "сделай шаг",
        "5 минут",
    )

    def __init__(self) -> None:
        self._client = None
        self.last_debug: dict[str, object] = {}
        self._model = "gpt-5-mini"

    def _resolve_model(self) -> str:
        return self._model

    @staticmethod
    def _strip_optional_followup_invitation(text: str) -> str:
        return _strip_optional_followup_invitation(text)

    @staticmethod
    def _build_no_practice_fallback_text(user_message: str) -> str:
        return _build_no_practice_fallback_text(user_message)

    @staticmethod
    def _normalize_name(raw_name: str) -> str | None:
        return _normalize_name(raw_name)


def _contract(*, user_message: str, conversation_context: str = "") -> WriterContract:
    bundle = MemoryBundle(
        conversation_context=conversation_context,
        user_profile=UserProfile(patterns=["avoidance"], values=["honesty"]),
        semantic_hits=[],
        has_relevant_knowledge=False,
        context_turns=2,
    )
    return WriterContract(
        user_message=user_message,
        thread_state=ThreadState(
            thread_id="th_1",
            user_id="u1",
            core_direction="тревога",
            phase="clarify",
            response_mode="reflect",
            response_goal="поддержка",
            nervous_state="window",
            openness="open",
            ok_position="I+W+",
            must_avoid=[],
            open_loops=[],
            safety_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        memory_bundle=bundle,
    )


def test_repair_greeting_without_mechanism_lecture_returns_contact_brief() -> None:
    agent = _ProbeAgent()
    result = agent._repair_greeting_without_mechanism_lecture(
        user_message="Привет! Как перестать наступать на одни и те же грабли?"
    )
    assert result.startswith("Привет.")
    assert "автоматический способ справляться" in result
    assert agent.last_debug["final_answer_shape"] == "contact_brief"


def test_resolve_one_step_or_no_practice_fallback_preserves_sanitized_direct_text() -> None:
    agent = _ProbeAgent()
    result = agent._resolve_one_step_or_no_practice_fallback(
        text=(
            "Понял — тебе тяжело, и это нормально. Не нужно сейчас ничего исправлять или заставлять себя. "
            "Можно остаться в разговоре без дополнительной нагрузки."
        ),
        user_message="без практик, просто скажи по-человечески",
        lowered_user="без практик, просто скажи по-человечески",
        canned_step_disallowed=True,
    )
    assert "сделай один шаг прямо сейчас" not in result.lower()
    assert agent.last_debug["final_answer_shape"] == "sanitized_direct_no_forced_practice"


def test_defer_no_stub_repair_sets_retry_payload_without_creating_replacement() -> None:
    agent = _ProbeAgent()
    result = agent._defer_no_stub_repair(
        signal="mvp_direct_concrete_request_repair",
        text="Прямой ответ. Если хочешь, можем продолжить дальше.",
        must_answer="скажи прямо",
    )
    assert result == "Прямой ответ"
    assert agent.last_debug["retry_recommended"] is True
    payload = agent.last_debug["no_stub_repair_signal"]
    assert isinstance(payload, dict)
    assert payload["recommended_action"] == "writer_retry"
    assert payload["user_facing_replacement_created"] is False


def test_get_client_returns_none_when_api_key_is_missing(monkeypatch: object) -> None:
    agent = _ProbeAgent()
    from bot_agent.multiagent.agents import writer_agent_fallback_state_mixin as mixin_module

    monkeypatch.setattr(mixin_module.config, "OPENAI_API_KEY", None, raising=False)
    assert agent._get_client() is None


def test_get_client_builds_async_openai_once_when_api_key_is_present(monkeypatch: object) -> None:
    agent = _ProbeAgent()
    from bot_agent.multiagent.agents import writer_agent_fallback_state_mixin as mixin_module

    created: list[str] = []

    class _FakeAsyncOpenAI:
        def __init__(self, *, api_key: str) -> None:
            created.append(api_key)

    fake_openai = ModuleType("openai")
    fake_openai.AsyncOpenAI = _FakeAsyncOpenAI
    monkeypatch.setattr(mixin_module.config, "OPENAI_API_KEY", "sk-test", raising=False)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    try:
        first = agent._get_client()
        second = agent._get_client()
    finally:
        sys.modules.pop("openai", None)
    assert first is second
    assert created == ["sk-test"]


def test_estimate_cost_uses_model_specific_rates() -> None:
    agent = _ProbeAgent()
    agent.last_debug["model"] = "gpt-4o-mini"
    assert agent._estimate_cost(tokens_prompt=1000, tokens_completion=500) == 0.00045


def test_extract_user_name_and_apply_name_continuity_support_ru_and_en() -> None:
    agent = _ProbeAgent()

    ru_contract = _contract(
        user_message="Мне тяжело. Меня зовут Анна.",
        conversation_context="assistant: понял",
    )
    assert agent._extract_user_name(ru_contract) == "Анна"
    assert agent._apply_name_continuity("Я рядом.", ru_contract) == "Анна, Я рядом."

    en_contract = _contract(
        user_message="My name is Alex and I feel stuck.",
        conversation_context="assistant: got it",
    )
    assert agent._extract_user_name(en_contract) == "Alex"


def test_apply_name_continuity_leaves_existing_name_and_missing_name_untouched() -> None:
    agent = _ProbeAgent()
    named_contract = _contract(user_message="Меня зовут Анна.")
    missing_contract = _contract(user_message="Просто тяжело.")

    assert agent._apply_name_continuity("Анна, я рядом.", named_contract) == "Анна, я рядом."
    assert agent._apply_name_continuity("Я рядом.", missing_contract) == "Я рядом."
