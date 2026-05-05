from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.feature_flags import feature_flags


def test_runtime_compatibility_defaults(monkeypatch) -> None:
    monkeypatch.delenv("MULTIAGENT_ENABLED", raising=False)
    monkeypatch.delenv("LEGACY_PIPELINE_ENABLED", raising=False)
    assert feature_flags.enabled("MULTIAGENT_ENABLED") is True
    assert feature_flags.enabled("LEGACY_PIPELINE_ENABLED") is False


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


def test_deprecated_runtime_flags_map_contains_legacy_runtime_switches() -> None:
    deprecated = feature_flags.deprecated_runtime_flags()
    assert deprecated["MULTIAGENT_ENABLED"] == "ignored_as_runtime_switch_after_PRD_036"
    assert deprecated["LEGACY_PIPELINE_ENABLED"] == "legacy_runtime_disabled_after_PRD_036"


def test_runtime_compatibility_flag_can_be_overridden_but_is_not_runtime_source(monkeypatch) -> None:
    monkeypatch.setenv("MULTIAGENT_ENABLED", "false")
    assert feature_flags.enabled("MULTIAGENT_ENABLED") is False
