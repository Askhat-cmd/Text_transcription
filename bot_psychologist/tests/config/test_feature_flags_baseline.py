from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.feature_flags import FeatureFlags


NEW_PHASE0_FLAGS = {
    "NEO_MINDBOT_ENABLED": False,
    "LEGACY_PIPELINE_ENABLED": True,
    "DISABLE_SD_RUNTIME": False,
    "DISABLE_USER_LEVEL_ADAPTER": False,
    "USE_NEW_DIAGNOSTICS_V1": False,
    "USE_DETERMINISTIC_ROUTE_RESOLVER": False,
}


def test_feature_flags_baseline_contains_phase0_flags() -> None:
    snapshot = FeatureFlags.snapshot()
    for name, default in NEW_PHASE0_FLAGS.items():
        assert name in snapshot
        assert snapshot[name] is default


def test_phase0_flags_can_be_toggled_independently(monkeypatch) -> None:
    monkeypatch.setenv("NEO_MINDBOT_ENABLED", "true")
    monkeypatch.setenv("LEGACY_PIPELINE_ENABLED", "false")
    monkeypatch.setenv("DISABLE_SD_RUNTIME", "true")
    monkeypatch.setenv("DISABLE_USER_LEVEL_ADAPTER", "true")
    monkeypatch.setenv("USE_NEW_DIAGNOSTICS_V1", "true")
    monkeypatch.setenv("USE_DETERMINISTIC_ROUTE_RESOLVER", "true")

    assert FeatureFlags.enabled("NEO_MINDBOT_ENABLED") is True
    assert FeatureFlags.enabled("LEGACY_PIPELINE_ENABLED") is False
    assert FeatureFlags.enabled("DISABLE_SD_RUNTIME") is True
    assert FeatureFlags.enabled("DISABLE_USER_LEVEL_ADAPTER") is True
    assert FeatureFlags.enabled("USE_NEW_DIAGNOSTICS_V1") is True
    assert FeatureFlags.enabled("USE_DETERMINISTIC_ROUTE_RESOLVER") is True
