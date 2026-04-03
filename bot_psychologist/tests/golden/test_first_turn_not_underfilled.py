from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_first_turn_not_underfilled() -> None:
    build = prompt_registry_v2.build(
        query="Привет, помоги понять, что со мной происходит",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="reflect",
        mode="PRESENCE",
        diagnostics={"interaction_mode": "coaching"},
        first_turn=True,
    )
    task = build.sections["TASK_INSTRUCTION"]
    assert "полноценный смысловой каркас" in task
    assert "Допустим один уточняющий вопрос" in task
    assert "Коротко, ясно и с одним рабочим вопросом" not in task
