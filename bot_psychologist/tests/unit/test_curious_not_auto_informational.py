from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive


def test_curious_not_auto_informational_prompt_override() -> None:
    prompt_key, prompt_text = adaptive.resolve_mode_prompt("curious", adaptive.config)
    assert prompt_key is None
    assert prompt_text is None


def test_explicit_informational_prompt_override_is_available() -> None:
    prompt_key, prompt_text = adaptive.resolve_mode_prompt("informational", adaptive.config)
    assert prompt_key == "prompt_mode_informational"
    assert isinstance(prompt_text, str)
    assert len(prompt_text.strip()) > 0
