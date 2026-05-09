from __future__ import annotations

import asyncio
import importlib
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.knowledge_policy import apply_knowledge_policy_v1
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="t_redact",
        user_id="u1",
        core_direction="test",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        continuity_score=0.9,
        created_at=now,
        updated_at=now,
    )


def _snapshot() -> StateSnapshot:
    return StateSnapshot(
        nervous_state="window",
        intent="explore",
        openness="open",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.8,
    )


def _bundle() -> MemoryBundle:
    marker = "INTERNAL_ONLY_RAW_TEXT_SHOULD_NOT_LEAK_046031"
    hits = [
        SemanticHit(
            chunk_id="internal_1",
            source="architecture",
            score=0.91,
            content=f"Very secret {marker} internal methodology text.",
            governance={
                "chunk_type": "style",
                "allowed_use": ["internal_only", "diagnostic_lens"],
                "safety_flags": ["source_style_not_user_facing"],
            },
        ),
        SemanticHit(
            chunk_id="quote_1",
            source="book",
            score=0.88,
            content="Длинный материал для цитаты " * 40,
            governance={
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            },
        ),
        SemanticHit(
            chunk_id="mixed_1",
            source="book",
            score=0.86,
            content="mixed high chunk",
            governance={
                "chunk_type": "theory",
                "allowed_use": ["writer_context"],
                "safety_flags": [],
            },
            chunking_quality={"mixed_intent_risk": True, "mixed_intent_severity": "high"},
        ),
        SemanticHit(
            chunk_id="legacy_1",
            source="legacy",
            score=0.6,
            content="legacy safe text",
        ),
    ]
    decisions, trace = apply_knowledge_policy_v1(hits)
    return MemoryBundle(
        conversation_context="User: hi",
        user_profile=UserProfile(),
        semantic_hits=hits,
        knowledge_rag_hits=[d.to_writer_hit_dict() for d in decisions if d.allowed_for_writer],
        has_relevant_knowledge=True,
        context_turns=4,
        knowledge_policy_trace=trace,
    )


def _patch_pipeline(monkeypatch) -> MultiAgentOrchestrator:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    monkeypatch.setattr(orch_module.state_analyzer_agent, "analyze", AsyncMock(return_value=_snapshot()))
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    orch_module.thread_manager_agent.last_debug = {
        "version": "thread_diagnostics_v1",
        "relation": {},
        "phase": {},
        "mode": {},
        "loops": {},
        "action": {},
        "summary_flags": [],
    }
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "assemble", AsyncMock(return_value=_bundle()))
    monkeypatch.setattr(orch_module.writer_agent, "write", AsyncMock(return_value="ok response"))
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _answer, _contract: ValidationResult(is_blocked=False),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.thread_storage, "archive_thread", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])
    return MultiAgentOrchestrator()


@pytest.mark.asyncio
async def test_orchestrator_knowledge_debug_redaction(monkeypatch) -> None:
    marker = "INTERNAL_ONLY_RAW_TEXT_SHOULD_NOT_LEAK_046031"
    orchestrator = _patch_pipeline(monkeypatch)
    result = await orchestrator.run(query="привет", user_id="u1")
    debug = result["debug"]
    detail = list(debug.get("semantic_hits_detail") or [])

    assert debug.get("semantic_hits_raw_redacted") is True
    assert isinstance(debug.get("knowledge_policy_trace"), dict)
    assert detail
    assert all("content_full" not in item for item in detail)

    serialized = json.dumps(debug, ensure_ascii=False)
    assert marker not in serialized

    by_id = {str(item.get("chunk_id")): item for item in detail}
    assert by_id["internal_1"]["policy_action"] == "internal_only"
    assert by_id["internal_1"]["content_preview"] == ""
    assert by_id["mixed_1"]["policy_action"] == "drop"
    assert by_id["mixed_1"]["content_preview"] == ""
    assert len(str(by_id["quote_1"]["content_preview"])) <= 80
    assert len(str(by_id["legacy_1"]["content_preview"])) <= 120
