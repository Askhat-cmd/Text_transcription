from __future__ import annotations

import pytest

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.philosophy_kernel import build_philosophy_kernel_runtime_payload


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = type("Usage", (), {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70})
        result = type("Result", (), {"output_text": "ok", "usage": usage})
        return result


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"calls": []})()})()


def _contract() -> WriterContract:
    thread_state = ThreadState(
        thread_id="t-1",
        user_id="u-1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
    )
    kernel_payload = build_philosophy_kernel_runtime_payload(
        user_message="Что такое нейросталкинг?",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    return WriterContract(
        user_message="Что такое нейросталкинг?",
        thread_state=thread_state,
        memory_bundle=MemoryBundle(has_relevant_knowledge=True),
        philosophy_kernel=kernel_payload,
        writer_freedom_contract=dict(kernel_payload.get("writer_freedom_contract", {})),
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "kb_grounding_available": True,
                "should_answer_directly": True,
            },
            "practice_gate": {"practice_allowed": False},
        },
    )


@pytest.mark.asyncio
async def test_writer_prompt_contains_kernel_and_freedom_blocks() -> None:
    client = _FakeClient()
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())
    user_prompt = str(client.responses.calls[0]["input"])

    assert "NEO PHILOSOPHY KERNEL" in user_prompt
    assert "WRITER FREEDOM CONTRACT" in user_prompt
    assert "internal_lens_not_citation" in user_prompt
    assert "speak_from_lens_not_about_lens" in user_prompt
    assert "mode_is_hint_not_cage=true" in user_prompt
    assert "practice_requires_gate=true" in user_prompt
    assert "hard_boundaries=" in user_prompt
    assert "RESPONSE PLANNER" in user_prompt


@pytest.mark.asyncio
async def test_writer_prompt_has_no_long_raw_source_passages() -> None:
    client = _FakeClient()
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())
    user_prompt = str(client.responses.calls[0]["input"])
    assert "Согласно Кузнице" not in user_prompt
    assert "В книге сказано" not in user_prompt
    assert len(user_prompt) < 14000


@pytest.mark.asyncio
async def test_writer_prompt_compactness_is_within_thresholds_for_representative_case() -> None:
    client = _FakeClient()
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())
    user_prompt = str(client.responses.calls[0]["input"])
    assert "prompt_compactness={" in user_prompt

    ctx = _contract().to_prompt_context()
    compactness = dict(ctx.get("philosophy_kernel_prompt_compactness", {}))
    assert int(compactness.get("philosophy_kernel_prompt_block_chars", 0)) <= 1800
    assert int(compactness.get("writer_freedom_contract_chars", 0)) <= 1000
    assert int(compactness.get("combined_chars", 0)) <= 2600
    assert bool(compactness.get("within_budget", False)) is True
