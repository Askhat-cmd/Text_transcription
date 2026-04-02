from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import PROMPT_STACK_ORDER, prompt_registry_v2


def test_prompt_stack_contract_v2_shape() -> None:
    build = prompt_registry_v2.build(
        query="Расскажи про нейросталкинг",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={
            "interaction_mode": "informational",
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "нейросталкинг",
        },
    )
    payload = build.as_dict()
    assert payload["version"] == "2.0"
    assert tuple(payload["order"]) == PROMPT_STACK_ORDER
    assert set(payload["sections"].keys()) == set(PROMPT_STACK_ORDER)

