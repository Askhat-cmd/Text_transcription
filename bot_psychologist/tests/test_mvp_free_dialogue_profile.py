from __future__ import annotations

from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


def test_dialogue_profile_default_is_safe_guided() -> None:
    assert str(getattr(config, "DIALOGUE_PROFILE", "safe_guided")) in {
        "safe_guided",
        "mvp_free_dialogue",
    }


def test_runtime_config_exposes_dialogue_profile_as_select() -> None:
    meta = RuntimeConfig.EDITABLE_CONFIG["DIALOGUE_PROFILE"]
    assert meta["type"] == "select"
    assert meta["group"] == "runtime"
    assert meta["options"] == ["safe_guided", "mvp_free_dialogue"]

