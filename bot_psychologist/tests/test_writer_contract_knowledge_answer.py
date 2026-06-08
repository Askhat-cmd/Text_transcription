from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = type("Usage", (), {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140})
        result = type("Result", (), {"output_text": "ok", "usage": usage})
        return result


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"calls": []})()})()


class _BadAnswerFakeResponses:
    def __init__(self, output_text: str) -> None:
        self.calls: list[dict] = []
        self._output_text = output_text

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = type("Usage", (), {"input_tokens": 90, "output_tokens": 30, "total_tokens": 120})
        result = type("Result", (), {"output_text": self._output_text, "usage": usage})
        return result


class _BadAnswerFakeClient:
    def __init__(self, output_text: str) -> None:
        self.responses = _BadAnswerFakeResponses(output_text)
        self.chat = type("Chat", (), {"completions": type("Completions", (), {"calls": []})()})()


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",  # type: ignore[arg-type]
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract() -> WriterContract:
    bundle = MemoryBundle(
        semantic_hits=[
            SemanticHit(
                chunk_id="k1",
                content="Нейросталкинг — это наблюдение за паттернами и триггерами.",
                source="kb",
                score=0.11,
            )
        ],
        has_relevant_knowledge=True,
    )
    return WriterContract(
        user_message='Ты вообще понимаешь что такое "Нейросталкинг"?',
        thread_state=_thread(),
        memory_bundle=bundle,
        knowledge_answer_guard={
            "schema_version": "knowledge_answer_routing_v1",
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "kb_grounding_available": True,
                "should_answer_directly": True,
                "should_ask_definition_first": False,
                "practice_allowed": False,
                "writer_instruction": "knowledge_answer_first; do_not_ask_user_to_define_term_before_answering",
            },
            "practice_gate": {
                "practice_allowed": False,
                "reason": "known_concept_answer_first",
            },
        },
    )


def test_writer_contract_prompt_context_contains_knowledge_answer_block() -> None:
    ctx = _contract().to_prompt_context()
    assert ctx["knowledge_answer"]["needed"] is True
    assert ctx["knowledge_answer"]["should_answer_directly"] is True
    assert ctx["practice_gate"]["practice_allowed"] is False
    assert ctx["practice_ban_enforced"] is True
    assert ctx["known_concept_clarification_ban"] is True
    assert ctx["external_surveillance_frame_ban"] is True


@pytest.mark.asyncio
async def test_writer_prompt_contains_knowledge_answer_routing_markers() -> None:
    client = _FakeClient()
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())

    user_input = str(client.responses.calls[0]["input"])
    assert "KNOWLEDGE ANSWER ROUTING" in user_input
    assert "knowledge_answer_first=true" in user_input
    assert "do_not_ask_user_to_define_term_before_answering=true" in user_input
    assert "practice_allowed=false" in user_input
    assert "practice_ban_instruction=no_exercise_but_answer_normally" in user_input
    assert "known_concept_clarification_ban=true" in user_input
    assert "external_surveillance_frame_ban=true" in user_input


@pytest.mark.asyncio
async def test_writer_post_enforces_known_concept_compliance() -> None:
    bad_answer = "Это внешнее слежение и биофидбек. О каком варианте ты говоришь?"
    client = _BadAnswerFakeClient(output_text=bad_answer)
    agent = WriterAgent(client=client, model="gpt-5-mini")
    fixed_answer = await agent.write(_contract())
    lowered = fixed_answer.lower()
    assert "внешнее слежение" not in lowered
    assert "биофидбек" not in lowered
    assert "о каком варианте" not in lowered
    assert "паттерн" in lowered
