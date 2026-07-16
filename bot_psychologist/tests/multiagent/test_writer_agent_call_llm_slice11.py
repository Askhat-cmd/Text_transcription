from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents import writer_agent_call_llm_slice11 as slice11_module
from bot_agent.multiagent.dialogue_policy import DIALOGUE_PROFILE_MVP_FREE
from bot_agent.multiagent.agents.writer_agent_prompts import (
    WRITER_SYSTEM,
    WRITER_SYSTEM_MVP_FREE_DIALOGUE,
)


EXPECTED_PATCH_KEYS = [
    "system_prompt",
    "dialogue_profile",
]


def test_apply_call_llm_slice11_uses_passed_profile_as_default_and_rebinds_it() -> None:
    resolve_runtime_settings = Mock(
        return_value={
            "model": "gpt-5-mini",
            "temperature": 0.7,
            "max_tokens": 1200,
            "timeout": 45,
        }
    )

    result = slice11_module._apply_call_llm_slice11_runtime_settings_and_system_prompt(
        {},
        dialogue_profile="SAFE_GUIDED",
        resolve_runtime_settings=resolve_runtime_settings,
    )

    assert result.dialogue_profile == "safe_guided"
    assert result.runtime_settings["model"] == "gpt-5-mini"
    assert result.system_prompt == WRITER_SYSTEM
    assert list(result.last_debug_patch.keys()) == EXPECTED_PATCH_KEYS
    assert result.last_debug_patch["system_prompt"] == WRITER_SYSTEM
    assert result.last_debug_patch["dialogue_profile"] == "safe_guided"
    resolve_runtime_settings.assert_called_once_with(dialogue_profile="safe_guided")


def test_apply_call_llm_slice11_ctx_profile_wins_and_selects_mvp_free_prompt() -> None:
    resolve_runtime_settings = Mock(
        return_value={
            "model": "gpt-5",
            "temperature": 0.9,
            "max_tokens": 1400,
            "timeout": 60,
        }
    )

    result = slice11_module._apply_call_llm_slice11_runtime_settings_and_system_prompt(
        {"dialogue_profile": DIALOGUE_PROFILE_MVP_FREE.upper()},
        dialogue_profile="safe_guided",
        resolve_runtime_settings=resolve_runtime_settings,
    )

    assert result.dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
    assert result.system_prompt == WRITER_SYSTEM_MVP_FREE_DIALOGUE
    assert result.last_debug_patch["system_prompt"] == WRITER_SYSTEM_MVP_FREE_DIALOGUE
    assert result.last_debug_patch["dialogue_profile"] == DIALOGUE_PROFILE_MVP_FREE
    resolve_runtime_settings.assert_called_once_with(
        dialogue_profile=DIALOGUE_PROFILE_MVP_FREE
    )


def test_apply_call_llm_slice11_non_mvp_profile_uses_standard_prompt() -> None:
    resolve_runtime_settings = Mock(return_value={"model": "gpt-5-nano"})

    result = slice11_module._apply_call_llm_slice11_runtime_settings_and_system_prompt(
        {"dialogue_profile": "safe_guided"},
        dialogue_profile=DIALOGUE_PROFILE_MVP_FREE,
        resolve_runtime_settings=resolve_runtime_settings,
    )

    assert result.dialogue_profile == "safe_guided"
    assert result.system_prompt == WRITER_SYSTEM
    assert list(result.last_debug_patch.keys()) == EXPECTED_PATCH_KEYS
    resolve_runtime_settings.assert_called_once_with(dialogue_profile="safe_guided")
