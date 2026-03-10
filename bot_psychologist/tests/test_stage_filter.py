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
        """Создать блок с complexity_score в шкале 1.0-10.0 (как в реальных данных).
        
        Для теста surface stage (complexity_cap=0.45):
        - complexity_score=2.0 → normalized=(2-1)/9=0.11 ≤ 0.45 ✓ проходит
        - complexity_score=7.0 → normalized=(7-1)/9=0.67 > 0.45 ✗ отсекается
        - complexity_score=9.0 → normalized=(9-1)/9=0.89 > 0.45 ✗ отсекается
        """
        self.complexity_score = complexity_score


def test_stage_filter_filters_retrieval_pairs_by_complexity() -> None:
    """Проверка что complexity_score нормализуется правильно (шкала 1-10 → 0-1)."""
    stage_filter = StageFilter()
    pairs = [
        # complexity_score=2.0 → normalized=0.11 ≤ 0.45 (surface cap) → проходит
        (_Block(2.0), 0.91),
        # complexity_score=7.0 → normalized=0.67 > 0.45 → отсекается
        (_Block(7.0), 0.85),
    ]
    filtered = stage_filter.filter_retrieval_pairs("surface", pairs)
    # Первый проходит по фильтру, второй отсекается но добавляется fallback (surface min=3, но есть только 2)
    assert len(filtered) == 2
    assert filtered[0][0].complexity_score == 2.0


def test_stage_filter_keeps_at_least_one_pair() -> None:
    """Проверка fallback — если все отсеклись, вернуть top-N по score.
    
    Для surface/awareness: min 3 блока (но не больше available).
    """
    stage_filter = StageFilter()
    pairs = [
        # complexity_score=9.0 → normalized=0.89 > 0.45 → отсекается
        (_Block(9.0), 0.95),
        # complexity_score=8.0 → normalized=0.78 > 0.45 → отсекается
        (_Block(8.0), 0.88),
    ]
    filtered = stage_filter.filter_retrieval_pairs("surface", pairs)
    # Fallback: вернуть top-2 (surface min=3, но available=2)
    assert len(filtered) == 2
    assert filtered[0][1] == 0.95  # top по score
