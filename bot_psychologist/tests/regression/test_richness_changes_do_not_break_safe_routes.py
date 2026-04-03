from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.output_validator import output_validator


def test_richness_changes_do_not_break_safe_routes() -> None:
    safe_short = output_validator.validate(
        "Сейчас важно снизить нагрузку и вернуть опору.",
        route="safe_override",
        mode="VALIDATION",
        safety_override=True,
        query="коротко",
    )
    assert safe_short.valid is True

    safe_forbidden = output_validator.validate(
        "Тебе обязательно сделай это немедленно.",
        route="safe_override",
        mode="VALIDATION",
        safety_override=True,
        query="что делать",
    )
    assert safe_forbidden.valid is False
    assert "forbidden_directive_advice" in safe_forbidden.errors
