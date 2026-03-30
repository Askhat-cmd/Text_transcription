from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.reranker_gate import should_rerank


def test_legacy_flag_keeps_always_on_behavior() -> None:
    run, reason = should_rerank(
        confidence_score=0.99,
        routing_mode="CLARIFICATION",
        retrieved_block_count=1,
        flags={"legacy_always_on": True, "RERANKER_ENABLED": False},
    )
    assert run is True
    assert reason == "legacy_voyage_enabled"


def test_disabled_when_new_flag_is_off() -> None:
    run, reason = should_rerank(
        confidence_score=0.20,
        routing_mode="THINKING",
        retrieved_block_count=20,
        flags={"legacy_always_on": False, "RERANKER_ENABLED": False},
    )
    assert run is False
    assert reason == "reranker_disabled_by_flag"


def test_enabled_by_low_confidence() -> None:
    run, reason = should_rerank(
        confidence_score=0.40,
        routing_mode="CLARIFICATION",
        retrieved_block_count=4,
        flags={"RERANKER_ENABLED": True, "RERANKER_CONFIDENCE_THRESHOLD": 0.55},
    )
    assert run is True
    assert reason.startswith("low_confidence=")


def test_enabled_by_mode_whitelist() -> None:
    run, reason = should_rerank(
        confidence_score=0.90,
        routing_mode="thinking",
        retrieved_block_count=2,
        flags={"RERANKER_ENABLED": True, "RERANKER_MODE_WHITELIST": "THINKING,INTERVENTION"},
    )
    assert run is True
    assert reason == "mode_in_whitelist=THINKING"


def test_enabled_by_block_count() -> None:
    run, reason = should_rerank(
        confidence_score=0.90,
        routing_mode="CLARIFICATION",
        retrieved_block_count=12,
        flags={"RERANKER_ENABLED": True, "RERANKER_BLOCK_THRESHOLD": 8},
    )
    assert run is True
    assert reason == "high_block_count=12"


def test_conditions_not_met() -> None:
    run, reason = should_rerank(
        confidence_score=0.90,
        routing_mode="CLARIFICATION",
        retrieved_block_count=4,
        flags={"RERANKER_ENABLED": True},
    )
    assert run is False
    assert reason == "conditions_not_met"
