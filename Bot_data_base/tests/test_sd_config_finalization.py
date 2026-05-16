from __future__ import annotations

from pathlib import Path

import yaml

from pipeline_runner import PipelineRunner


def test_sd_config_finalization_defaults() -> None:
    cfg = yaml.safe_load(Path("Bot_data_base/config.yaml").read_text(encoding="utf-8"))
    sd = cfg.get("sd_labeling", {})
    legacy = cfg.get("legacy_sd_labeling", {})

    assert sd.get("enabled") is False
    assert sd.get("explicit_legacy_mode") is False
    assert sd.get("deprecated") is True
    assert legacy.get("enabled") is False
    assert legacy.get("explicit_legacy_mode") is False


def test_legacy_sd_gate_requires_double_enable() -> None:
    assert PipelineRunner._is_legacy_sd_enabled({"enabled": False, "explicit_legacy_mode": False}) is False
    assert PipelineRunner._is_legacy_sd_enabled({"enabled": True, "explicit_legacy_mode": False}) is False
    assert PipelineRunner._is_legacy_sd_enabled({"enabled": False, "explicit_legacy_mode": True}) is False
    assert PipelineRunner._is_legacy_sd_enabled({"enabled": True, "explicit_legacy_mode": True}) is True
