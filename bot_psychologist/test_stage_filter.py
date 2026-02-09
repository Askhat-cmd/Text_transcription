#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for StageFilter."""

from bot_agent.retrieval import StageFilter


def test_stage_filter_blocks_intervention_on_surface() -> None:
    stage_filter = StageFilter()
    assert stage_filter.allow("surface", "INTERVENTION") is False
    assert stage_filter.allow("surface", "CLARIFICATION") is True


def test_stage_filter_allows_integration_only_late() -> None:
    stage_filter = StageFilter()
    assert stage_filter.allow("exploration", "INTEGRATION") is False
    assert stage_filter.allow("integration", "INTEGRATION") is True


def test_stage_filter_filters_candidates() -> None:
    stage_filter = StageFilter()
    candidates = ["PRESENCE", "INTERVENTION", "INTEGRATION"]
    filtered = stage_filter.filter_modes("awareness", candidates)
    assert filtered == ["PRESENCE"]


class _Block:
    def __init__(self, complexity_score: float) -> None:
        self.complexity_score = complexity_score


def test_stage_filter_filters_retrieval_pairs_by_complexity() -> None:
    stage_filter = StageFilter()
    pairs = [
        (_Block(0.2), 0.91),
        (_Block(0.7), 0.85),
    ]
    filtered = stage_filter.filter_retrieval_pairs("surface", pairs)
    assert len(filtered) == 1
    assert filtered[0][0].complexity_score == 0.2


def test_stage_filter_keeps_at_least_one_pair() -> None:
    stage_filter = StageFilter()
    pairs = [
        (_Block(0.9), 0.95),
        (_Block(0.8), 0.88),
    ]
    filtered = stage_filter.filter_retrieval_pairs("surface", pairs)
    assert len(filtered) == 1
    assert filtered[0][1] == 0.95
