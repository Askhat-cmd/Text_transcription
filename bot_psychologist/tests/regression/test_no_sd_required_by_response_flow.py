from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.answer_adaptive import _build_llm_prompts
from bot_agent.response import ResponseGenerator


class _DummyAnswerer:
    def build_system_prompt(self) -> str:
        return "BASE SYSTEM"

    def build_context_prompt(self, blocks, query, conversation_history="") -> str:
        joined_titles = ", ".join(getattr(block, "title", "") for block in blocks)
        return f"Q={query}; titles={joined_titles}; ctx={conversation_history}"


def test_response_flow_does_not_require_sd_primary() -> None:
    generator = ResponseGenerator(answerer=_DummyAnswerer())
    blocks = [SimpleNamespace(title="Block A", content="content")]

    system_prompt, user_prompt = _build_llm_prompts(
        response_generator=generator,
        query="почему это важно",
        blocks=blocks,
        conversation_context="",
        user_level_adapter=None,
        sd_level=None,
        mode_prompt="MODE",
        additional_system_context="",
        mode_prompt_override=None,
        mode_overrides_sd=False,
    )

    assert "BASE SYSTEM" in system_prompt
    assert "Q=почему это важно" in user_prompt
