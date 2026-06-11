from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from bot_agent.multiagent.hybrid_retrieval_planner import build_hybrid_retrieval_plan_v1


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_greeting_uses_universal_gate() -> None:
    result = await build_hybrid_retrieval_plan_v1(
        user_message="Привет",
        planner_mode="apply",
        client=None,
    )

    assert result["valid"] is True
    assert result["llm_called"] is False
    assert result["universal_gate"] == "greeting"
    assert result["plan"]["retrieval_action"] == "suppress_rag"


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_clear_kb_ask_no_llm() -> None:
    result = await build_hybrid_retrieval_plan_v1(
        user_message="Что такое нейросталкинг?",
        planner_mode="apply",
        client=None,
    )

    assert result["valid"] is True
    assert result["llm_called"] is False
    assert result["universal_gate"] == "clear_kb_ask"
    assert result["plan"]["retrieval_action"] == "query_kb"
    assert "нейросталкинг" in result["plan"]["composed_query"]
    assert result["plan"]["writer_can_ignore_rag"] is False


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_accepts_valid_llm_json(monkeypatch) -> None:
    async def _fake_completion(**kwargs):
        payload = {
            "retrieval_needed": True,
            "retrieval_action": "query_kb_and_memory",
            "composed_query": "контроль паника механизм безопасность",
            "needed_chunk_types": ["mechanism", "safety", "dialogue_move"],
            "avoided_chunk_types": [],
            "mechanism_hints": ["control_as_safety", "loss_of_control_as_threat"],
            "depth_level_hint": 1,
            "safety_layer_required": True,
            "allowed_use_filter_hint": ["writer_support", "diagnostic_hint"],
            "diagnostic_hints_used": False,
            "writer_can_ignore_rag": True,
            "retrieval_gap_reason": "",
            "no_user_facing_text_created": True,
            "fallback_if_invalid": "legacy_query",
            "constraints_for_writer": ["no_theory"],
            "confidence": 0.83,
        }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            tokens_prompt=11,
            tokens_completion=22,
            tokens_total=33,
        )

    monkeypatch.setattr(
        "bot_agent.multiagent.hybrid_retrieval_planner.create_agent_completion",
        _fake_completion,
    )

    result = await build_hybrid_retrieval_plan_v1(
        user_message="Да, но на моём примере и без теории",
        planner_mode="apply",
        client=object(),
    )

    assert result["valid"] is True
    assert result["llm_called"] is True
    assert result["fallback_used"] is False
    assert result["plan"]["retrieval_action"] == "query_kb_and_memory"
    assert result["plan"]["needed_chunk_types"] == ["mechanism", "safety", "dialogue_move"]


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_routes_contextual_explain_to_llm(monkeypatch) -> None:
    async def _fake_completion(**kwargs):
        payload = {
            "retrieval_needed": True,
            "retrieval_action": "query_kb",
            "composed_query": "пример механизм",
            "needed_chunk_types": ["mechanism"],
            "avoided_chunk_types": [],
            "mechanism_hints": [],
            "depth_level_hint": 1,
            "safety_layer_required": False,
            "allowed_use_filter_hint": ["writer_support"],
            "diagnostic_hints_used": False,
            "writer_can_ignore_rag": True,
            "retrieval_gap_reason": "missing_chunk_type_metadata",
            "no_user_facing_text_created": True,
            "fallback_if_invalid": "legacy_query",
            "constraints_for_writer": [],
            "confidence": 0.77,
        }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            tokens_prompt=11,
            tokens_completion=22,
            tokens_total=33,
        )

    monkeypatch.setattr(
        "bot_agent.multiagent.hybrid_retrieval_planner.create_agent_completion",
        _fake_completion,
    )

    result = await build_hybrid_retrieval_plan_v1(
        user_message="Объясни это на моем примере",
        planner_mode="apply",
        client=object(),
    )

    assert result["llm_called"] is True
    assert result["plan"]["retrieval_action"] == "query_kb"
    assert result["plan"]["retrieval_gap_reason"] == "missing_chunk_type_metadata"


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_rejects_invalid_llm_json(monkeypatch) -> None:
    async def _fake_completion(**kwargs):
        payload = {
            "retrieval_needed": True,
            "retrieval_action": "query_kb",
            "composed_query": "скажи пользователю что он в безопасности",
            "needed_chunk_types": ["mechanism"],
            "no_user_facing_text_created": False,
            "confidence": 0.9,
        }
        return SimpleNamespace(
            text=json.dumps(payload, ensure_ascii=False),
            tokens_prompt=11,
            tokens_completion=22,
            tokens_total=33,
        )

    monkeypatch.setattr(
        "bot_agent.multiagent.hybrid_retrieval_planner.create_agent_completion",
        _fake_completion,
    )

    result = await build_hybrid_retrieval_plan_v1(
        user_message="Да, но на моём примере",
        planner_mode="apply",
        client=object(),
    )

    assert result["valid"] is False
    assert result["fallback_used"] is True
    assert result["plan"]["retrieval_action"] == "trace_only"
    assert result["error"] == "no_user_facing_text_created_must_be_true"


@pytest.mark.asyncio
async def test_hybrid_retrieval_planner_safety_adds_loss_of_control_hint() -> None:
    result = await build_hybrid_retrieval_plan_v1(
        user_message="У жены паника, она говорит, что если перестанет контролировать, то умрет",
        planner_mode="apply",
        client=None,
    )

    assert result["plan"]["retrieval_action"] == "query_kb"
    assert "loss_of_control_as_threat" in result["plan"]["mechanism_hints"]
