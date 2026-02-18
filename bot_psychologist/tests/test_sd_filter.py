#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SD retrieval filter."""

from dataclasses import dataclass, field

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
    assert [block.block_id for block, _ in filtered] == ["b1", "b2", "b3", "b4"]
