from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _overlay_payload() -> dict:
    return {
        "prd_id": "PRD-047.20",
        "batch_id": "batch_1",
        "evaluation_only": True,
        "human_final_approval": False,
        "summary": {"accepted_item_count": 1},
        "items": [
            {
                "candidate_id": "cand-1",
                "chunk_type": "mechanism",
                "risk_level": "medium",
                "source_ref": {
                    "heading_path": ["РљРѕРЅС‚СЂРѕР»СЊ РєР°Рє Р·Р°С‰РёС‚Р°"],
                    "content_preview": "RAW SOURCE MUST STAY OUT",
                },
                "accepted_fields": {
                    "summary_candidate": "РљРѕРЅС‚СЂРѕР»СЊ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїРѕРїС‹С‚РєРѕР№ СЃРѕС…СЂР°РЅРёС‚СЊ Р±РµР·РѕРїР°СЃРЅРѕСЃС‚СЊ.",
                    "core_thesis_candidate": "РљРѕРіРґР° СЃС‚СЂР°С€РЅРѕ, РєРѕРЅС‚СЂРѕР»СЊ РёРЅРѕРіРґР° СЃС‚Р°РЅРѕРІРёС‚СЃСЏ Р·Р°С‰РёС‚РѕР№.",
                    "safe_user_translation_candidate": "РџРѕС…РѕР¶Рµ, РєРѕРЅС‚СЂРѕР»СЊ Р·РґРµСЃСЊ СЂР°Р±РѕС‚Р°РµС‚ РєР°Рє Р·Р°С‰РёС‚Р°.",
                    "allowed_writer_use_candidate": "РўРѕР»СЊРєРѕ РєР°Рє РјСЏРіРєР°СЏ РіРёРїРѕС‚РµР·Р°.",
                    "mechanism_hints_candidates": ["control_as_safety"],
                },
            }
        ],
    }


def _thread() -> ThreadState:
    now = datetime.utcnow()
    return ThreadState(
        thread_id="overlay_shadow_t",
        user_id="u1",
        core_direction="x",
        phase="clarify",
        relation_to_thread="continue",
        response_mode="reflect",
        continuity_score=0.9,
        active_frame={"active_concept": "СЃС‚СЂР°С…"},
        created_at=now,
        updated_at=now,
    )


async def _run_case(monkeypatch: pytest.MonkeyPatch, *, overlay_enabled: bool, overlay_path: Path) -> dict:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    captured_contract: dict[str, str] = {}

    async def _write(contract):
        captured_contract["prompt_context"] = json.dumps(contract.to_prompt_context(), ensure_ascii=False)
        return "writer answer"

    monkeypatch.setenv("OVERLAY_SHADOW_TRACE_ENABLED", "true" if overlay_enabled else "false")
    monkeypatch.setenv("OVERLAY_SHADOW_OVERLAY_FILE", str(overlay_path))
    monkeypatch.setenv("OVERLAY_SHADOW_MAX_MATCHES", "3")
    monkeypatch.setenv("HYBRID_RETRIEVAL_PLANNER_MODE", "off")

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(return_value=StateSnapshot("window", "explore", "open", "I+W+", False, 0.8)),
    )
    monkeypatch.setattr(
        orch_module.thread_manager_agent,
        "update",
        AsyncMock(return_value=_thread()),
    )
    orch_module.thread_manager_agent.last_debug = {
        "version": "thread_diagnostics_v1",
        "relation": {"continuity_risk": "none"},
        "phase": {},
        "mode": {},
        "loops": {},
        "action": {"thread_action": "continue"},
        "summary_flags": [],
    }
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(
            return_value=MemoryBundle(
                conversation_context="ctx",
                has_relevant_knowledge=True,
                context_turns=2,
                rag_query="РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј",
                semantic_hits=[
                    {
                        "chunk_id": "h1",
                        "source": "doc_1",
                        "score": 0.91,
                        "content": "РєРѕРЅС‚РµРЅС‚ С‡Р°РЅРєР°",
                    }
                ],
                rag_retrieval_trace={"executed_rag_query": "РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј"},
                hybrid_retrieval_trace={
                    "executed_rag_query": "РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј",
                    "legacy_rag_query": "РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј",
                    "planned_composed_query": "РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј",
                    "query_before_rag_proof": False,
                },
            )
        ),
    )
    monkeypatch.setattr(orch_module.writer_agent, "write", _write)
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _a, _c: ValidationResult(is_blocked=False),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.thread_storage, "archive_thread", lambda *_a, **_k: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])

    result = await MultiAgentOrchestrator().run(query="РјРЅРµ СЃС‚СЂР°С€РЅРѕ РїРѕС‚РµСЂСЏС‚СЊ РєРѕРЅС‚СЂРѕР»СЊ", user_id="u1")
    return {
        "result": result,
        "prompt_context": captured_contract["prompt_context"],
    }


@pytest.mark.asyncio
async def test_overlay_shadow_trace_does_not_leak_into_writer_or_change_behavior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    overlay_path = tmp_path / "overlay.json"
    overlay_path.write_text(json.dumps(_overlay_payload(), ensure_ascii=False), encoding="utf-8")

    off_case = await _run_case(monkeypatch, overlay_enabled=False, overlay_path=overlay_path)
    on_case = await _run_case(monkeypatch, overlay_enabled=True, overlay_path=overlay_path)

    off_debug = off_case["result"]["debug"]
    on_debug = on_case["result"]["debug"]

    assert off_case["result"]["answer"] == on_case["result"]["answer"] == "writer answer"
    assert off_debug["executed_rag_query"] == on_debug["executed_rag_query"] == "РєРѕРЅС‚СЂРѕР»СЊ СЃС‚СЂР°С… РјРµС…Р°РЅРёР·Рј"
    assert off_debug["semantic_hits_count"] == on_debug["semantic_hits_count"] == 1
    assert off_case["prompt_context"] == on_case["prompt_context"]
    assert "overlay_shadow" not in on_case["prompt_context"]
    assert "cand-1" not in on_case["prompt_context"]
    assert "RAW SOURCE MUST STAY OUT" not in on_case["prompt_context"]

    on_shadow = on_debug["overlay_shadow"]
    assert on_shadow["enabled"] is True
    assert on_shadow["used_for_writer"] is False
    assert on_shadow["used_for_retrieval_execution"] is False
    assert on_shadow["used_for_final_answer"] is False
    assert on_shadow["would_help"] is True

    off_shadow = off_debug["overlay_shadow"]
    assert off_shadow["enabled"] is False
    assert off_shadow["reason"] == "disabled_by_config"

