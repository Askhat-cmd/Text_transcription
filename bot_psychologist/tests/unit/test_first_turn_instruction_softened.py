from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.onboarding_flow import build_first_turn_instruction


def test_first_turn_instruction_softened() -> None:
    instruction = build_first_turn_instruction().lower()
    assert "полноценный" in instruction
    assert "смысловой каркас" in instruction
    assert "не заменяет основную часть ответа" in instruction
    assert "1 короткое отражение + 1 рабочий вопрос" not in instruction
