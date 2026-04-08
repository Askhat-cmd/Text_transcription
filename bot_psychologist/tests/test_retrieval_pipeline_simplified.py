#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration-style checks for simplified retrieval pipeline."""

from types import SimpleNamespace

import pytest

import bot_agent.answer_adaptive as aa
from bot_agent.data_loader import Block
from bot_agent.state_classifier import StateAnalysis, UserState


class DummyMemory:
    def __init__(self) -> None:
        self.turns = []
        self.summary = ""
        self.summary_updated_at = None
        self.semantic_memory = SimpleNamespace(last_hits_detail=[], last_hits_count=0)
        self.metadata = {}
        self.working_state = None

    def get_adaptive_context_text(self, _query: str) -> str:
        return ""

    def get_last_turns(self, _n: int):
        return []

    def get_turns_preview(self):
        return []

    def get_user_sd_profile(self):
        return {}

    def update_sd_profile(self, *_args, **_kwargs):
        return None

    def set_working_state(self, working_state):
        self.working_state = working_state

    def add_turn(self, user_input: str, bot_response: str, **_kwargs):
        self.turns.append(
            SimpleNamespace(
                timestamp="now",
                user_input=user_input,
                bot_response=bot_response,
                user_state=None,
                blocks_used=0,
                concepts=[],
            )
        )

    def get_summary(self) -> str:
        return self.summary


class DummyRetriever:
    def __init__(self, blocks):
        self.blocks = blocks
        self.last_kwargs = {}

    def retrieve(self, _query, top_k=None, author_id=None, **kwargs):
        self.last_kwargs = dict(kwargs)
        return [(block, 1.0 - idx * 0.01) for idx, block in enumerate(self.blocks)]


class DummyReranker:
    calls = 0

    def __init__(self, model="rerank-2", enabled=True) -> None:
        self.model = model
        self.enabled = enabled

    def rerank_pairs(self, _query, candidates, top_k=1):
        DummyReranker.calls += 1
        if self.enabled:
            return list(candidates)[:top_k]
        return list(candidates)


class DummyResponseGenerator:
    last_call = None
    class _DummyAnswerer:
        @staticmethod
        def build_context_prompt(blocks, query, conversation_history=None):
            return f"Q: {query}\nBlocks: {len(blocks)}"

    def __init__(self):
        self.answerer = self._DummyAnswerer()

    def generate(self, query, blocks, **kwargs):
        DummyResponseGenerator.last_call = {
            "query": query,
            "blocks": blocks,
            **kwargs,
        }
        return {
            "answer": "ok",
            "model_used": "dummy",
            "tokens_prompt": 1,
            "tokens_completion": 1,
            "tokens_total": 2,
            "error": None,
        }


class DummyDecisionGate:
    routing = None

    def __init__(self) -> None:
        self.scorer = SimpleNamespace(suggest_block_cap=lambda available, _level: min(int(available), 5))

    def route(self, *_args, **_kwargs):
        return DummyDecisionGate.routing


def _make_blocks(count: int):
    return [
        Block(block_id=f"b{idx}", title=f"Title {idx}", content=f"Content {idx}")
        for idx in range(count)
    ]


def _setup_pipeline(
    monkeypatch,
    blocks,
    *,
    voyage_enabled: bool,
    fast_path: bool,
    sd_level: str = "ORANGE",
    reranker_enabled: bool = False,
):
    dummy_memory = DummyMemory()
    dummy_retriever = DummyRetriever(blocks)

    async def fake_state_classifier(*_args, **_kwargs):
        return StateAnalysis(
            primary_state=UserState.CURIOUS,
            confidence=0.6,
            secondary_states=[],
            indicators=[],
            emotional_tone="neutral",
            depth="intermediate",
            recommendations=["respond calmly"],
        )

    decision = SimpleNamespace(route="CLARIFICATION", reason="test", forbid=[], rule_id="R1")
    routing = SimpleNamespace(
        mode="CLARIFICATION",
        decision=decision,
        confidence_score=0.5,
        confidence_level="medium",
        stage="surface",
    )
    DummyDecisionGate.routing = routing

    monkeypatch.setattr(aa.data_loader, "load_all_data", lambda: None)
    monkeypatch.setattr(aa, "get_conversation_memory", lambda _user_id: dummy_memory)
    monkeypatch.setattr(aa.state_classifier, "classify", fake_state_classifier)
    monkeypatch.setattr(aa, "DecisionGate", DummyDecisionGate)
    monkeypatch.setattr(aa, "detect_routing_signals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(aa, "get_retriever", lambda: dummy_retriever)
    monkeypatch.setattr(aa, "VoyageReranker", DummyReranker)
    monkeypatch.setattr(aa, "ResponseGenerator", DummyResponseGenerator)
    monkeypatch.setattr(aa, "_should_use_fast_path", lambda *_args, **_kwargs: fast_path)
    # В тестах игнорируем реальные admin overrides, чтобы значения были детерминированными
    monkeypatch.setattr(
        aa.config,
        "_load_overrides",
        lambda: {"config": {}, "prompts": {}, "meta": {}, "history": []},
    )
    monkeypatch.setattr(aa.config, "VOYAGE_ENABLED", voyage_enabled)
    monkeypatch.setattr(aa.config, "RERANKER_ENABLED", reranker_enabled)
    monkeypatch.setattr(aa.config, "RERANKER_CONFIDENCE_THRESHOLD", 0.55)
    monkeypatch.setattr(aa.config, "RERANKER_MODE_WHITELIST", "THINKING,INTERVENTION")
    monkeypatch.setattr(aa.config, "RERANKER_BLOCK_THRESHOLD", 8)
    monkeypatch.setattr(aa.config, "VOYAGE_TOP_K", 5)
    monkeypatch.setattr(aa.config, "TOP_K_BLOCKS", 5)
    monkeypatch.setattr(aa.feature_flags, "enabled", lambda _name: True)
    DummyReranker.calls = 0

    return dummy_retriever


def test_pipeline_voyage_enabled_caps_to_five(monkeypatch):
    blocks = _make_blocks(7)
    _setup_pipeline(monkeypatch, blocks, voyage_enabled=True, fast_path=False)

    result = aa.answer_question_adaptive(
        query="Что такое осознанность?",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace["blocks_after_cap"] == 5
    assert "pre_routing_result" not in trace
    assert "pre_rerank_result" not in trace
    assert len(trace.get("llm_calls", [])) <= 2
    assert float(trace.get("total_duration_ms") or 0.0) <= 5000.0
    assert not any("stage_filter" in stage["name"] for stage in trace["pipeline_stages"])


def test_pipeline_voyage_disabled_fallback_still_caps(monkeypatch):
    blocks = _make_blocks(7)
    _setup_pipeline(monkeypatch, blocks, voyage_enabled=False, fast_path=False)

    result = aa.answer_question_adaptive(
        query="Почему так происходит?",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace["blocks_after_cap"] == 5
    assert trace.get("reranker_enabled") is False
    assert trace.get("rerank_reason") == "reranker_disabled_by_flag"


def test_pipeline_fast_path_skips_blocks(monkeypatch):
    blocks = _make_blocks(7)
    _setup_pipeline(monkeypatch, blocks, voyage_enabled=True, fast_path=True)

    result = aa.answer_question_adaptive(
        query="привет",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace["fast_path"] is False
    assert trace["blocks_after_cap"] == 5
    assert trace["recommended_mode"] in {"PRESENCE", "CLARIFICATION"}


def test_sd_level_not_passed_to_retriever_query(monkeypatch):
    blocks = _make_blocks(7)
    retriever = _setup_pipeline(monkeypatch, blocks, voyage_enabled=True, fast_path=False, sd_level="ORANGE")

    result = aa.answer_question_adaptive(
        query="Хочу понять свои паттерны избегания.",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace["blocks_after_cap"] == 5
    assert isinstance(DummyResponseGenerator.last_call["sd_level"], str)
    assert "sd_level" not in retriever.last_kwargs


def test_pipeline_conditional_reranker_skips_when_conditions_not_met(monkeypatch):
    blocks = _make_blocks(5)
    _setup_pipeline(
        monkeypatch,
        blocks,
        voyage_enabled=False,
        reranker_enabled=True,
        fast_path=False,
        sd_level="ORANGE",
    )
    monkeypatch.setattr(aa.config, "RERANKER_CONFIDENCE_THRESHOLD", 0.1)

    result = aa.answer_question_adaptive(
        query="Нужна краткая справка",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace.get("rerank_should_run") is False
    assert trace.get("rerank_reason") == "conditions_not_met"
    assert DummyReranker.calls == 0


def test_pipeline_feature_flag_disables_conditional_reranker(monkeypatch):
    blocks = _make_blocks(5)
    _setup_pipeline(
        monkeypatch,
        blocks,
        voyage_enabled=False,
        reranker_enabled=True,
        fast_path=False,
        sd_level="ORANGE",
    )
    monkeypatch.setattr(aa.feature_flags, "enabled", lambda name: False if name == "ENABLE_CONDITIONAL_RERANKER" else True)

    result = aa.answer_question_adaptive(
        query="Нужна краткая справка",
        user_id="test_user",
        debug=True,
    )

    trace = result["debug_trace"]
    assert trace.get("rerank_should_run") is False
    assert trace.get("rerank_reason") == "reranker_disabled_by_flag"
    assert DummyReranker.calls == 0
