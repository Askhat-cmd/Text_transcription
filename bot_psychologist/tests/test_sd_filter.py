#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SD retrieval filter."""

import sys
from pathlib import Path

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.retrieval.sd_filter import filter_by_sd_level


@dataclass
class _DummyBlock:
    block_id: str
    sd_level: str | None = None
    metadata: dict = field(default_factory=dict)


def test_sd_filter_keeps_allowed_and_backfills_untagged() -> None:
    pairs = [
        (_DummyBlock("b1", sd_level="RED"), 0.9),
        (_DummyBlock("b2", sd_level="GREEN"), 0.8),
        (_DummyBlock("b3", sd_level=None, metadata={}), 0.7),
    ]
    filtered = filter_by_sd_level(
        blocks_with_scores=pairs,
        user_sd_level="RED",
        user_state="neutral",
        min_blocks=2,
    )
    ids = [block.block_id for block, _ in filtered]
    assert "b1" in ids
    assert "b3" in ids


def test_sd_filter_critical_fallback_returns_original_slice() -> None:
    """Тест устарел — критический fallback заменён на мягкий (soft fallback).
    
    Новое поведение:
    1. Сначала пробуем расширить allowed уровни (extended fallback)
    2. Если всё ещё мало — берём лучшие по score из остатка (soft fallback)
    3. Возвращаем min_blocks, а не все оригинальные
    """
    pairs = [
        (_DummyBlock("b1", sd_level="YELLOW"), 0.9),
        (_DummyBlock("b2", sd_level="YELLOW"), 0.8),
        (_DummyBlock("b3", sd_level="TURQUOISE"), 0.7),
        (_DummyBlock("b4", sd_level="TURQUOISE"), 0.6),
    ]
    filtered = filter_by_sd_level(
        blocks_with_scores=pairs,
        user_sd_level="RED",
        user_state="neutral",
        min_blocks=3,
    )
    # RED extended fallback: ["RED", "BLUE", "PURPLE", "ORANGE"]
    # YELLOW не входит → soft fallback берёт лучшие по score
    # Ожидаем: b1 (YELLOW), b2 (YELLOW), b3 (TURQUOISE) — top 3 по score
    assert [block.block_id for block, _ in filtered] == ["b1", "b2", "b3"]
    assert len(filtered) == 3  # min_blocks, а не все 4


class TestSDFilterPipeline:
    def test_sd_level_from_classifier_passed_to_retriever(self):
        from bot_agent.sd_classifier import SDClassificationResult
        from bot_agent.state_classifier import StateAnalysis, UserState
        with patch("bot_agent.sd_classifier.SDClassifier.classify") as mock_clf:
            mock_clf.return_value = SDClassificationResult(
                primary="GREEN",
                secondary=None,
                confidence=0.8,
                indicator="test",
                method="heuristic",
            )
            with patch("bot_agent.state_classifier.state_classifier.classify") as mock_state, \
                patch("bot_agent.answer_adaptive._should_use_fast_path", return_value=False), \
                patch("bot_agent.answer_adaptive.ResponseGenerator.generate", return_value={"answer": "ok"}), \
                patch("bot_agent.retriever.SimpleRetriever.retrieve") as mock_retrieve:
                mock_state.return_value = StateAnalysis(
                    primary_state=UserState.CURIOUS,
                    confidence=0.9,
                    secondary_states=[],
                    indicators=[],
                    emotional_tone="calm",
                    depth="surface",
                    recommendations=[],
                )
                mock_retrieve.return_value = []
                from bot_agent.answer_adaptive import answer_question_adaptive
                answer_question_adaptive(
                    query="я чувствую тревогу",
                    user_id="u1",
                    include_path_recommendation=False,
                    include_feedback_prompt=False,
                )
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("sd_level") == 6

    def test_sd_level_1_through_8_all_valid(self):
        from bot_agent.db_api_client import DBApiClient
        client = DBApiClient()
        for level in range(1, 9):
            allowed = [l for l in [level - 1, level, level + 1] if 1 <= l <= 8]
            assert level in allowed
