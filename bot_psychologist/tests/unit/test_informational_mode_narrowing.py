from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier


def test_informational_mode_narrowing_keeps_personal_mixed_query_in_coaching() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Объясни избегание, потому что мне кажется это про меня",
        state_analysis=None,
        informational_mode_hint=True,
    )
    assert diagnostics.interaction_mode == "coaching"


def test_informational_mode_narrowing_keeps_practice_entry_query_in_coaching() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Объясни, что такое избегание и как начать это практиковать",
        state_analysis=None,
        informational_mode_hint=True,
    )
    assert diagnostics.interaction_mode == "coaching"


def test_informational_mode_narrowing_keeps_pure_definition_in_informational() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Объясни, что такое самоосознание",
        state_analysis=None,
        informational_mode_hint=True,
    )
    assert diagnostics.interaction_mode == "informational"
