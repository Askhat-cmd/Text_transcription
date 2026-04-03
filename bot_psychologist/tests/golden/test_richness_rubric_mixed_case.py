from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_richness_rubric_mixed_case() -> None:
    build = prompt_registry_v2.build(
        query="Объясни избегание и как это увидеть у себя",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="reflect",
        mode="THINKING",
        diagnostics={"interaction_mode": "coaching"},
        mixed_query_bridge=True,
    )

    task = build.sections["TASK_INSTRUCTION"].lower()
    assert "сначала коротко обозначь концепт" in task
    assert "свяжи его с запросом пользователя" in task
    assert "практический угол" in task
    assert "мягкий вопрос-мост" in task
