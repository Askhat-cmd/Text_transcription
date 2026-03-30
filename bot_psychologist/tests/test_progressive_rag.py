#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ProgressiveRAG block weighting."""

from bot_agent.progressive_rag import ProgressiveRAG


def test_progressive_rag_boosts_weight_and_reranks(tmp_path) -> None:
    db_path = tmp_path / "progressive_rag.db"
    rag = ProgressiveRAG(str(db_path))

    # Initially block b is ranked higher by raw score.
    blocks = [
        (type("Block", (), {"block_id": "a"})(), 0.40),
        (type("Block", (), {"block_id": "b"})(), 0.60),
        (type("Block", (), {"block_id": "c"})(), 0.55),
    ]

    for _ in range(5):
        rag.record_positive_feedback("a")

    reranked = rag.rerank_by_weights(blocks)
    top_ids = [item[0].block_id for item in reranked[:3]]
    assert "a" in top_ids[:1]
    assert rag.get_weight("a") > 1.0


def test_progressive_rag_reset_restores_default_weight(tmp_path) -> None:
    db_path = tmp_path / "progressive_rag.db"
    rag = ProgressiveRAG(str(db_path))
    rag.record_positive_feedback("x")
    assert rag.get_weight("x") > 1.0

    rag.reset_weights()
    assert rag.get_weight("x") == 1.0
