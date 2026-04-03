from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.output_validator import output_validator


def test_output_validator_anti_sparse_rules_detect_underfilled_inform_answer() -> None:
    text = "Избегание — это стратегия ухода от напряжения. Что из этого тебе ближе?"
    result = output_validator.validate(
        text,
        route="inform",
        mode="CLARIFICATION",
        query="Объясни избегание и чем оно отличается от осознанного выбора",
    )
    assert result.valid is False
    assert "underfilled_inform_answer" in result.errors
    assert result.needs_regeneration is True


def test_output_validator_anti_sparse_rules_add_regeneration_hint() -> None:
    hint = output_validator.build_regeneration_hint(
        ["underfilled_inform_answer"],
        route="inform",
        mode="CLARIFICATION",
        query="Чем отличается самоосознание от самонаблюдения?",
    ).lower()
    assert "сравни по 2-3 критериям" in hint
    assert "добавь 2-4 коротких примера" in hint
