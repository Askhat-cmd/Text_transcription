from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.output_validator import output_validator


def test_output_validator_repairs_markdown_and_certainty() -> None:
    raw = "### Заголовок\n```text\nпример\n```\nЭто гарантированно поможет."
    result = output_validator.validate(raw, route="inform", mode="CLARIFICATION")
    assert result.valid is True
    assert "```" not in result.text
    assert "гарантированно" not in result.text.lower()
    assert result.repair_applied is True


def test_output_validator_blocks_forbidden_directive_in_safe_override() -> None:
    raw = "Тебе обязательно сделай это немедленно."
    result = output_validator.validate(raw, route="safe_override", mode="VALIDATION", safety_override=True)
    assert result.valid is False
    assert "forbidden_directive_advice" in result.errors
    assert result.needs_regeneration is True

