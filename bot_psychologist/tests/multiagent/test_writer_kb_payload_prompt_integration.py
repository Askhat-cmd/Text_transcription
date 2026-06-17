from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeCompletions:
    def __init__(self, payload: str = "ok") -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=30, total_tokens=130),
        )


class _FakeResponses:
    def __init__(self, payload: str = "ok") -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=100, output_tokens=30, total_tokens=130),
        )


class _FakeClient:
    def __init__(self, payload: str = "ok") -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload))
        self.responses = _FakeResponses(payload=payload)


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id="u1",
        core_direction="нейросталкинг",
        phase="clarify",
        response_mode="reflect",
        response_goal="объяснить по сути",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract() -> WriterContract:
    knowledge_text = (
        "**Нейросталкинг** — это наблюдение за триггерами, реакциями и повторяющимися связками.\n\n"
        "**НеоСталкинг** — это второй этаж, где человек видит уже не отдельный импульс, "
        "а конфигурацию механизма и может выбирать действие точнее."
    )
    bundle = MemoryBundle(
        conversation_context="User: что такое нейросталкинг?\nAssistant: ...",
        user_profile=UserProfile(),
        knowledge_rag_hits=[
            {
                "chunk_id": "c1",
                "source": "123__kuznica_duha",
                "content": knowledge_text,
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )
    return WriterContract(
        user_message="что такое нейросталкинг?",
        thread_state=_thread(),
        memory_bundle=bundle,
        retrieval_decision={
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "c1",
                    "source": "123__kuznica_duha",
                    "content": knowledge_text,
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
            "rag_included_reason": "selected_for_writer",
        },
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )


@pytest.mark.asyncio
async def test_writer_prompt_contains_structured_payload_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_EXCERPT_TARGET_CHARS", "110")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_EXCERPT_MAX_CHARS", "140")
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")

    await agent._call_llm(_contract())

    user_input = str(agent._client.responses.calls[0]["input"])
    assert "WRITER KB PAYLOAD" in user_input
    assert "version=writer_kb_payload_v1" in user_input
    assert "chunk_count=1" in user_input
    assert "content_excerpt:" in user_input
    assert "**НеоСталкинг** — это в" not in user_input
    assert agent.last_debug["writer_kb_payload_trace"]["payload_chunk_count"] == 1


@pytest.mark.asyncio
async def test_disabled_flag_keeps_legacy_fallback_available(monkeypatch) -> None:
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "false")
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")

    await agent._call_llm(_contract())

    user_input = str(agent._client.responses.calls[0]["input"])
    assert "WRITER KB PAYLOAD" in user_input
    assert "version=legacy_semantic_hits_fallback_v1" in user_input
    assert "legacy_hits:" in user_input


@pytest.mark.asyncio
async def test_builder_failure_falls_back_safely(monkeypatch) -> None:
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")
    import bot_agent.multiagent.writer_context_package as writer_context_package_module

    def _boom(**_: object) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(writer_context_package_module, "build_writer_kb_payload", _boom)
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")

    await agent._call_llm(_contract())

    user_input = str(agent._client.responses.calls[0]["input"])
    assert "version=legacy_semantic_hits_fallback_v1" in user_input
    assert "writer_kb_payload_empty_or_failed" in user_input or "boom" in user_input
    assert "writer_kb_payload_failed" in list(agent.last_debug["writer_kb_payload_trace"].get("warnings", []))
