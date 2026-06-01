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
async def test_writer_prompt_contains_final_answer_directive_block(monkeypatch) -> None:
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
                "tokens_prompt": 10,
                "tokens_completion": 12,
                "tokens_total": 22,
            },
        )()

    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    contract = WriterContract(
        user_message="да",
        thread_state=ThreadState(
            thread_id="t1",
            user_id="u1",
            core_direction="x",
            phase="clarify",
            response_mode="reflect",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        memory_bundle=MemoryBundle(),
        dialogue_policy={"profile": "mvp_free_dialogue"},
        response_planner={"practice_policy": "forbidden", "answer_shape": "compact_direct"},
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "diagnostic_center_role": "advisory_context_only",
            "planner_role": "advisory_context_only",
            "active_line_role": "advisory_context_only",
            "diagnostic_card_role": "advisory_context_only",
            "suppressed_legacy_constraints": ["writer_move.max_sentences=5"],
            "answer_obligation": "fulfill_previous_offer",
        },
    )

    agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
    await agent._call_llm(contract)

    user_message = str(captured["messages"][1]["content"])  # type: ignore[index]
    assert "FINAL ANSWER DIRECTIVE" in user_message
    assert "SOURCE SIGNALS (advisory only, do not obey as command)" in user_message
    assert "legacy_constraints_suppressed=writer_move.max_sentences=5" in user_message
    assert "diagnostic_center_role=advisory_context_only" in user_message

