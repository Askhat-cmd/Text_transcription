#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ConfidenceScorer."""

from bot_agent.retrieval import ConfidenceScorer


def test_confidence_scorer_low_level() -> None:
    scorer = ConfidenceScorer()
    result = scorer.score(
        {
            "local_similarity": 0.2,
            "voyage_confidence": 0.2,
            "delta_top1_top2": 0.1,
            "state_match": 0.2,
            "question_clarity": 0.1,
        }
    )
    assert result.level == "low"
    assert 0.0 <= result.score < 0.4


def test_confidence_scorer_high_level() -> None:
    scorer = ConfidenceScorer()
    result = scorer.score(
        {
            "local_similarity": 0.9,
            "voyage_confidence": 0.95,
            "delta_top1_top2": 0.8,
            "state_match": 0.85,
            "question_clarity": 0.9,
        }
    )
    assert result.level == "high"
    assert result.score >= 0.75


def test_confidence_suggests_block_cap() -> None:
    scorer = ConfidenceScorer()
    assert scorer.suggest_block_cap(5, "low") == 2
    assert scorer.suggest_block_cap(5, "medium") == 3
    assert scorer.suggest_block_cap(5, "high") == 5
