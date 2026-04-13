from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.feature_flags import feature_flags


def test_feature_flags_toggle_independently(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EMBEDDING_PROVIDER", "false")
    monkeypatch.setenv("ENABLE_CONDITIONAL_RERANKER", "true")
    monkeypatch.setenv("ENABLE_FAST_STATE_DETECTOR", "false")
    monkeypatch.setenv("USE_OUTPUT_VALIDATION", "false")

    assert feature_flags.enabled("ENABLE_EMBEDDING_PROVIDER") is False
    assert feature_flags.enabled("ENABLE_CONDITIONAL_RERANKER") is True
    assert feature_flags.enabled("ENABLE_FAST_STATE_DETECTOR") is False
    assert feature_flags.enabled("USE_OUTPUT_VALIDATION") is False


def test_unknown_feature_flag_returns_false() -> None:
    assert feature_flags.enabled("UNKNOWN_FLAG") is False
