from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.diagnostics_classifier import diagnostics_classifier
from bot_agent.prompt_registry_v2 import prompt_registry_v2
from bot_agent.route_resolver import route_resolver


def test_practice_entry_not_glossary_like() -> None:
    query = "Как начать это практиковать без перегруза?"
    diagnostics = diagnostics_classifier.classify(
        query=query,
        state_analysis=None,
        informational_mode_hint=True,
    )
    route = route_resolver.resolve(diagnostics)
    assert route.route != "inform"

    build = prompt_registry_v2.build(
        query=query,
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route=route.route,
        mode=route.mode,
        diagnostics=diagnostics.as_dict(),
    )
    task = build.sections["TASK_INSTRUCTION"].lower()
    assert "избегай смысловой скупости" in task
