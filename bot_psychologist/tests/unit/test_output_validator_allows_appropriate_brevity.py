from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.output_validator import output_validator


def test_output_validator_allows_appropriate_brevity_for_safe_override() -> None:
    result = output_validator.validate(
        "Сейчас важно снизить нагрузку и вернуть опору.",
        route="safe_override",
        mode="VALIDATION",
        safety_override=True,
        query="Мне очень плохо, коротко помоги",
    )
    assert result.valid is True


def test_output_validator_allows_appropriate_brevity_for_regulate() -> None:
    result = output_validator.validate(
        "Сделай медленный выдох и опиши, что меняется в теле.",
        route="regulate",
        mode="VALIDATION",
        query="коротко, что делать прямо сейчас",
    )
    assert result.valid is True


def test_output_validator_allows_explicit_short_preference_in_inform_route() -> None:
    result = output_validator.validate(
        "Избегание — это способ уйти от напряжения.",
        route="inform",
        mode="CLARIFICATION",
        query="Кратко: что такое избегание?",
    )
    assert result.valid is True
