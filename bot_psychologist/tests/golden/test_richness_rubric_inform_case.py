from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def _rubric_inform(build) -> dict:
    style = build.sections["A_STYLE_POLICY"].lower()
    task = build.sections["TASK_INSTRUCTION"].lower()
    return {
        "explanation_depth": "раскрывай" in style or "раскрой" in task,
        "comparison_present": "сравни" in task,
        "examples_present": "2-4" in style,
        "practical_relevance": "практический" in style,
        "tone_not_flat": "живо" in style,
    }


def test_richness_rubric_inform_case() -> None:
    build = prompt_registry_v2.build(
        query="Чем самоосознание отличается от самонаблюдения?",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={"interaction_mode": "informational"},
    )
    rubric = _rubric_inform(build)
    assert all(rubric.values()), rubric
