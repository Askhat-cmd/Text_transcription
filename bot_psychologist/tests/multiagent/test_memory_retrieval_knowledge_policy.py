from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents.memory_retrieval import MemoryRetrievalAgent
from bot_agent.multiagent.contracts.memory_bundle import SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="core",
        phase="clarify",
    )


@pytest.mark.asyncio
async def test_memory_retrieval_applies_policy_before_knowledge_hits(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_recent_turns", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent, "_load_personal_history_context", AsyncMock(return_value=[]))
    monkeypatch.setattr(agent, "_load_semantic_memory_hits", AsyncMock(return_value=[]))

    hits = [
        SemanticHit(
            chunk_id="practice_1",
            content="Шаг 1: вдох. Шаг 2: выдох.",
            source="practice",
            score=0.95,
            governance={
                "chunk_type": "practice",
                "allowed_use": ["writer_context", "practice_suggestion"],
                "safety_flags": ["not_for_direct_quote"],
            },
            chunking_quality={"mixed_intent_risk": False, "mixed_intent_severity": "none"},
        ),
        SemanticHit(
            chunk_id="internal_1",
            content="Внутренний стиль source material",
            source="architecture",
            score=0.92,
            governance={
                "chunk_type": "style",
                "allowed_use": ["internal_only", "diagnostic_lens"],
                "safety_flags": ["source_style_not_user_facing"],
            },
            chunking_quality={"mixed_intent_risk": False, "mixed_intent_severity": "none"},
        ),
        SemanticHit(
            chunk_id="mixed_1",
            content="смешанный high risk",
            source="mixed",
            score=0.9,
            governance={
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": [],
            },
            chunking_quality={"mixed_intent_risk": True, "mixed_intent_severity": "high"},
        ),
        SemanticHit(
            chunk_id="legacy_1",
            content="legacy content",
            source="legacy",
            score=0.55,
        ),
    ]
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=hits))

    bundle = await agent.assemble(user_message="вопрос", thread_state=_thread(), user_id="u1")

    writer_ids = [h.get("chunk_id") for h in bundle.knowledge_rag_hits]
    assert "practice_1" in writer_ids
    assert "legacy_1" in writer_ids
    assert "internal_1" not in writer_ids
    assert "mixed_1" not in writer_ids

    for hit in bundle.knowledge_rag_hits:
        assert "governance_summary" in hit
        if hit["chunk_id"] == "practice_1":
            assert len(hit["content"]) <= 240

    trace = bundle.knowledge_policy_trace
    assert trace.get("version") == "knowledge_policy_trace_v1"
    assert trace.get("input_hits_count") == 4
    assert trace.get("internal_only_count", 0) >= 1
    assert trace.get("dropped_count", 0) >= 1

    # No internal raw content must leak into writer hits.
    assert all("Внутренний стиль" not in str(item.get("content", "")) for item in bundle.knowledge_rag_hits)
