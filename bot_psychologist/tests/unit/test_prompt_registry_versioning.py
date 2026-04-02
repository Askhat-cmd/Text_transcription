from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import PROMPT_STACK_VERSION, prompt_registry_v2


def test_prompt_registry_v2_version_metadata() -> None:
    build = prompt_registry_v2.build(
        query="Что такое окно толерантности?",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics=None,
    )
    payload = build.as_dict()
    assert payload["version"] == PROMPT_STACK_VERSION
    assert payload["version"] == "2.0"
    assert "AA_SAFETY" in payload["order"]
    assert "TASK_INSTRUCTION" in payload["sections"]

