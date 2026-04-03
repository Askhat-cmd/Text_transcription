from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_difference_question_has_real_comparison() -> None:
    build = prompt_registry_v2.build(
        query="Чем самоосознание отличается от самонаблюдения?",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={"interaction_mode": "informational"},
    )
    task = build.sections["TASK_INSTRUCTION"].lower()
    assert "если запрос просит различия" in task
    assert "2-3 критериям" in task
