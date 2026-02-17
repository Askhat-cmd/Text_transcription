#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for VoyageReranker fallback behavior."""

from types import SimpleNamespace

from bot_agent.retrieval import RerankItem, VoyageReranker


def test_voyage_reranker_fallback_sorting() -> None:
    reranker = VoyageReranker(enabled=False)
    items = [
        RerankItem(text="a", payload=1, score=0.2),
        RerankItem(text="b", payload=2, score=0.9),
        RerankItem(text="c", payload=3, score=0.4),
    ]
    top = reranker.rerank("query", items, top_k=2)
    assert [x.payload for x in top] == [2, 3]


def test_voyage_reranker_pairs_fallback() -> None:
    reranker = VoyageReranker(enabled=False)
    candidates = [
        (SimpleNamespace(title="x", summary="sx"), 0.1),
        (SimpleNamespace(title="y", summary="sy"), 0.8),
    ]
    top = reranker.rerank_pairs("query", candidates, top_k=1)
    assert len(top) == 1
    assert top[0][1] == 0.8
