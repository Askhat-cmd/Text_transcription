from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.onboarding_flow import detect_phase8_signals


def test_phase8_narrowing_does_not_mark_generic_rasskazhi_as_informational() -> None:
    signals = detect_phase8_signals("Расскажи о системе нейросталкинга", turns_count=2)
    assert signals.informational_intent is False


def test_phase8_narrowing_keeps_definition_as_informational() -> None:
    signals = detect_phase8_signals("Что такое нейросталкинг?", turns_count=2)
    assert signals.informational_intent is True


def test_phase8_narrowing_marks_practice_entry_as_mixed() -> None:
    signals = detect_phase8_signals(
        "Объясни, что такое избегание и как начать это практиковать",
        turns_count=2,
    )
    assert signals.informational_intent is True
    assert signals.mixed_query is True

