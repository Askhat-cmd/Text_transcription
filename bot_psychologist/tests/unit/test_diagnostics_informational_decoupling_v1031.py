from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier


def test_diagnostics_decoupling_generic_rasskazhi_is_not_informational() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Расскажи о системе нейросталкинга",
        state_analysis=None,
        informational_mode_hint=False,
    )
    assert diagnostics.interaction_mode == "coaching"


def test_diagnostics_decoupling_definition_query_remains_informational() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Что такое нейросталкинг?",
        state_analysis=None,
        informational_mode_hint=True,
    )
    assert diagnostics.interaction_mode == "informational"

