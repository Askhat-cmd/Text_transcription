from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_informational_answer_not_sparse() -> None:
    build = prompt_registry_v2.build(
        query="Объясни, что такое избегание",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={"interaction_mode": "informational"},
    )
    task = build.sections["TASK_INSTRUCTION"].lower()
    style = build.sections["A_STYLE_POLICY"].lower()

    assert "избегай смысловой скупости" in task
    assert "не своди ответ к формату" in task
    assert "2-4" in style
