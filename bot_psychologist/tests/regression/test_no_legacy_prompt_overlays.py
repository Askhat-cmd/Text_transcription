from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.response.response_generator import ResponseGenerator


class _FakeAnswerer:
    def __init__(self) -> None:
        self.last_system_prompt = ""

    def build_system_prompt(self) -> str:
        return "BASE_PROMPT"

    def generate_answer(self, *_args, **_kwargs):
        self.last_system_prompt = self.build_system_prompt()
        return {
            "answer": "ok",
            "model_used": "test-model",
            "tokens_used": 1,
            "tokens_prompt": 1,
            "tokens_completion": 1,
            "tokens_total": 2,
            "llm_call_info": {},
            "error": None,
        }


def test_system_prompt_override_bypasses_legacy_sd_overlay(monkeypatch) -> None:
    answerer = _FakeAnswerer()
    generator = ResponseGenerator(answerer=answerer)

    def _boom(_sd_level: str) -> str:
        raise AssertionError("legacy SD overlay must not be called")

    monkeypatch.setattr(generator, "_load_sd_prompt", _boom)

    result = generator.generate(
        "Что делать?",
        blocks=[],
        mode="PRESENCE",
        confidence_level="medium",
        system_prompt_override="STACK_V2_PROMPT",
    )
    assert result["error"] is None
    assert answerer.last_system_prompt == "STACK_V2_PROMPT"

