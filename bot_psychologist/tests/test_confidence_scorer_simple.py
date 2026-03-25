#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit checks for simplified confidence scorer."""

from bot_agent.retrieval import ConfidenceScorer


def test_voyage_confidence_does_not_affect_score():
    scorer = ConfidenceScorer()
    signals_base = {
        "local_similarity": 0.4,
        "delta_top1_top2": 0.4,
        "state_match": 0.4,
        "question_clarity": 0.4,
    }
    score_base = scorer.score(signals_base).score
    signals_with_voyage = dict(signals_base, voyage_confidence=1.0)
    score_with_voyage = scorer.score(signals_with_voyage).score
    assert score_base == score_with_voyage


def test_fast_path_enabled_for_low_score():
    scorer = ConfidenceScorer()
    result = scorer.score(
        {
            "local_similarity": 0.1,
            "delta_top1_top2": 0.1,
            "state_match": 0.1,
            "question_clarity": 0.1,
        }
    )
    assert result.level == "low"
    assert result.score < 0.4


def test_fast_path_not_enabled_for_high_score():
    scorer = ConfidenceScorer()
    result = scorer.score(
        {
            "local_similarity": 0.9,
            "delta_top1_top2": 0.9,
            "state_match": 0.9,
            "question_clarity": 0.9,
        }
    )
    assert result.level in {"medium", "high"}
    assert result.score >= 0.4
