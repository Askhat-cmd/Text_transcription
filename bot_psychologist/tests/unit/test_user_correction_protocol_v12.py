from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.onboarding_flow import detect_phase8_signals
from bot_agent.output_validator import output_validator


def test_user_correction_signal_detects_new_phrases() -> None:
    signals = detect_phase8_signals("Объясни проще, пожалуйста, слишком сложно и непонятно", turns_count=4)
    assert signals.user_correction is True


def test_output_validator_rejects_short_correction_answer() -> None:
    result = output_validator.validate(
        "Понял. Уточню.",
        route="reflect",
        mode="THINKING",
        query="непонятно, объясни проще",
    )
    assert result.needs_regeneration is True
    assert "user_correction_too_short" in result.errors
    assert "user_correction_missing_question" in result.errors


def test_output_validator_accepts_full_correction_answer() -> None:
    answer = (
        "Похоже, я объяснил слишком сложно. "
        "Смысл проще: тревога сейчас сужает внимание, поэтому решение не видно сразу. "
        "Например, это как пытаться читать мелкий текст в темноте — сначала нужен свет и опора. "
        "Так понятнее?"
    )
    result = output_validator.validate(
        answer,
        route="reflect",
        mode="THINKING",
        query="ты отвечаешь непонятно, объясни проще",
    )
    assert result.needs_regeneration is False
