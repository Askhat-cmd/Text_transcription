from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.feature_flags import FeatureFlags


NEW_PHASE0_FLAGS = {
    "NEO_MINDBOT_ENABLED": True,
    "LEGACY_PIPELINE_ENABLED": False,
    "DISABLE_SD_RUNTIME": True,
    "DISABLE_USER_LEVEL_ADAPTER": True,
    "SD_CLASSIFIER_ENABLED": False,
    "USER_LEVEL_ADAPTER_ENABLED": False,
    "PRE_ROUTING_ENABLED": False,
    "USE_NEW_DIAGNOSTICS_V1": True,
    "USE_DETERMINISTIC_ROUTE_RESOLVER": True,
}


def test_feature_flags_baseline_contains_phase0_flags() -> None:
    snapshot = FeatureFlags.snapshot()
    for name, default in NEW_PHASE0_FLAGS.items():
        assert name in snapshot
        assert snapshot[name] is default


def test_phase0_flags_can_be_toggled_independently(monkeypatch) -> None:
    monkeypatch.setenv("NEO_MINDBOT_ENABLED", "false")
    monkeypatch.setenv("LEGACY_PIPELINE_ENABLED", "true")
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "false")
    monkeypatch.setenv("DISABLE_USER_LEVEL_ADAPTER", "false")
    monkeypatch.setenv("SD_CLASSIFIER_ENABLED", "true")
    monkeypatch.setenv("USER_LEVEL_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("PRE_ROUTING_ENABLED", "true")
    monkeypatch.setenv("USE_NEW_DIAGNOSTICS_V1", "false")
    monkeypatch.setenv("USE_DETERMINISTIC_ROUTE_RESOLVER", "false")

    assert FeatureFlags.enabled("NEO_MINDBOT_ENABLED") is False
    assert FeatureFlags.enabled("LEGACY_PIPELINE_ENABLED") is True
    assert FeatureFlags.enabled("DISABLE_SD_RUNTIME") is False
    assert FeatureFlags.enabled("DISABLE_USER_LEVEL_ADAPTER") is False
    assert FeatureFlags.enabled("SD_CLASSIFIER_ENABLED") is True
    assert FeatureFlags.enabled("USER_LEVEL_ADAPTER_ENABLED") is True
    assert FeatureFlags.enabled("PRE_ROUTING_ENABLED") is True
    assert FeatureFlags.enabled("USE_NEW_DIAGNOSTICS_V1") is False
    assert FeatureFlags.enabled("USE_DETERMINISTIC_ROUTE_RESOLVER") is False
