from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier
from bot_agent.route_resolver import route_resolver


def test_golden_case_panic_goes_to_regulate() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Мне срочно плохо, паника и тревога накрывают",
        state_analysis=None,
    )
    route = route_resolver.resolve(diagnostics)
    assert diagnostics.nervous_system_state == "hyper"
    assert route.route == "regulate"


def test_golden_case_reflective_question_goes_to_reflect() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Почему я снова избегаю и как это связано с чувством вины?",
        state_analysis=None,
    )
    route = route_resolver.resolve(diagnostics)
    assert diagnostics.request_function in {"understand", "explore"}
    assert route.route == "reflect"


def test_golden_case_informational_query_goes_to_inform() -> None:
    diagnostics = diagnostics_classifier.classify(
        query="Объясни, что такое когнитивное слияние",
        state_analysis=None,
        informational_mode_hint=True,
    )
    route = route_resolver.resolve(diagnostics)
    assert diagnostics.interaction_mode == "informational"
    assert route.route == "inform"
