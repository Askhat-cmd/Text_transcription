from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.onboarding_flow import build_mixed_query_instruction


def test_mixed_query_instruction_enriched() -> None:
    instruction = build_mixed_query_instruction().lower()
    assert "практический" in instruction
    assert "заметить или проверить" in instruction
    assert "содержательного раскрытия" in instruction
