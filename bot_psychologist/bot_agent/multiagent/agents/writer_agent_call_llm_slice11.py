from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..dialogue_policy import (
    DIALOGUE_PROFILE_MVP_FREE,
    normalize_dialogue_profile,
)
from .writer_agent_prompts import (
    WRITER_SYSTEM,
    WRITER_SYSTEM_MVP_FREE_DIALOGUE,
)


@dataclass(frozen=True)
class CallLLMSlice11RuntimeSettingsAndSystemPromptResult:
    dialogue_profile: str
    runtime_settings: dict[str, Any]
    system_prompt: str
    last_debug_patch: dict[str, Any]


def _apply_call_llm_slice11_runtime_settings_and_system_prompt(
    ctx: dict[str, Any],
    *,
    dialogue_profile: str,
    resolve_runtime_settings: Callable[..., dict[str, Any]],
) -> CallLLMSlice11RuntimeSettingsAndSystemPromptResult:
    dialogue_profile = normalize_dialogue_profile(
        ctx.get("dialogue_profile", dialogue_profile)
    )
    runtime_settings = resolve_runtime_settings(dialogue_profile=dialogue_profile)
    system_prompt = (
        WRITER_SYSTEM_MVP_FREE_DIALOGUE
        if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
        else WRITER_SYSTEM
    )
    last_debug_patch: dict[str, Any] = {
        "system_prompt": system_prompt,
        "dialogue_profile": dialogue_profile,
    }
    return CallLLMSlice11RuntimeSettingsAndSystemPromptResult(
        dialogue_profile=dialogue_profile,
        runtime_settings=runtime_settings,
        system_prompt=system_prompt,
        last_debug_patch=last_debug_patch,
    )
