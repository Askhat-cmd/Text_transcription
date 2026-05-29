from __future__ import annotations

from datetime import datetime
import importlib

import pytest

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _DummyClient:
    pass


@pytest.mark.asyncio
async def test_writer_uses_mvp_free_system_prompt_and_higher_tokens(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    captured: dict[str, object] = {}

    async def _fake_completion(**kwargs):
        captured.update(kwargs)
        return type(
            "Result",
            (),
            {
                "text": "ok",
                "api_mode": "responses_api",
                "tokens_prompt": 12,
                "tokens_completion": 18,
                "tokens_total": 30,
            },
        )()

    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    contract = WriterContract(
        user_message="объясни максимально подробно, что такое нейросталкинг",
        thread_state=ThreadState(
            thread_id="t1",
            user_id="u1",
            core_direction="concept",
            phase="clarify",
            response_mode="reflect",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        memory_bundle=MemoryBundle(),
        dialogue_policy={"profile": "mvp_free_dialogue", "expansion_requested": True},
        response_planner={
            "enabled": True,
            "next_move": "answer_known_concept",
            "answer_shape": "concept_explanation_full",
            "response_depth": "deep",
            "question_policy": "none",
            "practice_policy": "forbidden",
            "revoicing_policy": "suppressed",
        },
    )

    agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
    await agent._call_llm(contract)

    system_message = captured["messages"][0]["content"]  # type: ignore[index]
    assert "developer-local MVP free dialogue режиме" in str(system_message)
    assert int(captured["max_tokens"]) >= 2500
    user_message = captured["messages"][1]["content"]  # type: ignore[index]
    assert "MVP FREE DIALOGUE OVERRIDES:" in str(user_message)
    assert "context_budget_chars=" in str(user_message)
