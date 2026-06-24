from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeResponses:
    def __init__(self, payload: str = "ok") -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
        )


class _FakeClient:
    def __init__(self, payload: str = "ok") -> None:
        self.responses = _FakeResponses(payload=payload)
        self.chat = SimpleNamespace(completions=None)


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="prd-047-30-thread",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="reflect",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _bundle() -> MemoryBundle:
    return MemoryBundle(
        conversation_context="User: Мне тяжело.\nAssistant: ...",
        user_profile=UserProfile(),
        knowledge_rag_hits=[
            {
                "chunk_id": "kb-1",
                "source": "internal_doc",
                "content": "Internal knowledge chunk about the concept.",
                "allowed_use": ["writer_support"],
                "chunking_quality": {"chunk_type": "concept"},
            }
        ],
        has_relevant_knowledge=True,
        context_turns=2,
    )


def test_writer_contract_exposes_grounding_authority_without_visible_grounding(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "true")

    contract = WriterContract(
        user_message="Мне тяжело и меня бесит эта ситуация.",
        thread_state=_thread(),
        memory_bundle=_bundle(),
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_suppressed_reason": "non_kb_emotional_support_turn",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about the concept.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "answer_obligation": "answer_direct_question",
            "must_answer": "Мне тяжело и меня бесит эта ситуация.",
            "answer_shape": "direct_answer",
            "depth": "short",
            "style": "simple, brief",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
            "diagnostic_center_role": "advisory_context_only",
            "planner_role": "advisory_context_only",
            "active_line_role": "advisory_context_only",
            "diagnostic_card_role": "advisory_context_only",
            "writer_autonomy": "medium",
            "latest_turn_constraints_v1": {
                "version": "latest_turn_constraints_v1",
                "no_practice": False,
                "no_breathing_only": False,
                "simplify": False,
                "long_term_perspective": False,
                "no_internal_db": False,
                "active_constraints": [],
                "source": "latest_user_turn_explicit_text",
            },
        },
    )

    ctx = contract.to_prompt_context()
    directive = json.loads(ctx["writer_visible_final_answer_directive_json"])

    assert ctx["writer_grounding_visibility_v1"]["kb_visible_to_writer"] is False
    assert ctx["semantic_hits"] == []
    assert "Safety and the explicit latest user request are mandatory" in ctx["writer_grounding_authority_note"]
    assert directive["grounding_authority"]["kb_semantic_cards_diagnostic_hints"] == "optional_grounding"
    assert directive["grounding_visibility"]["kb_visible_to_writer"] is False


@pytest.mark.asyncio
async def test_writer_prompt_does_not_leak_legacy_hits_when_grounding_hidden(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SEMANTIC_CARDS_PILOT_ENABLED", "true")
    monkeypatch.setenv("WRITER_KB_PAYLOAD_ENABLED", "false")
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")

    contract = WriterContract(
        user_message="Мне тяжело и просто поддержи.",
        thread_state=_thread(),
        memory_bundle=_bundle(),
        retrieval_decision={
            "retrieval_action": "trace_only",
            "retrieval_need": "none",
            "rag_suppressed_reason": "non_kb_emotional_support_turn",
            "rag_included_count": 1,
            "rag_included_for_writer": [
                {
                    "chunk_id": "kb-1",
                    "source": "internal_doc",
                    "content": "Internal knowledge chunk about the concept.",
                    "allowed_use": ["writer_support"],
                    "chunking_quality": {"chunk_type": "concept"},
                }
            ],
        },
    )

    await agent._call_llm(contract)

    user_input = str(agent._client.responses.calls[0]["input"])
    assert "Internal knowledge chunk about the concept." not in user_input
    assert "grounding_visibility_json" in user_input
    assert '"kb_visible_to_writer": false' in user_input.lower()
