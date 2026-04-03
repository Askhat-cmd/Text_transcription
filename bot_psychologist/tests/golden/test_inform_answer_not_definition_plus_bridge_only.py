from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.output_validator import output_validator


def test_inform_answer_not_definition_plus_bridge_only() -> None:
    result = output_validator.validate(
        "Самоосознание — это наблюдение за собой. Что из этого тебе ближе?",
        route="inform",
        mode="CLARIFICATION",
        query="Чем самоосознание отличается от самонаблюдения?",
    )
    assert result.valid is False
    assert "underfilled_inform_answer" in result.errors
    assert any(item.startswith("sparse_") for item in result.warnings)
