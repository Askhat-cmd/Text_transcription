from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import PROMPT_STACK_ORDER, prompt_registry_v2


class _Block:
    def __init__(self, title: str, summary: str) -> None:
        self.title = title
        self.summary = summary


def test_prompt_stack_order_is_fixed() -> None:
    build = prompt_registry_v2.build(
        query="Объясни, что происходит со мной в этом цикле",
        blocks=[_Block("Цикл избегания", "Шаги цикла и триггеры.")],
        conversation_context="Пользователь ранее описал тревогу и усталость.",
        additional_system_context="state=curious",
        route="reflect",
        mode="PRESENCE",
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "avoidance loop",
        },
    )
    assert tuple(build.order) == PROMPT_STACK_ORDER
    assert build.system_prompt.index("## AA_SAFETY") < build.system_prompt.index("## A_STYLE_POLICY")
    assert build.system_prompt.index("## A_STYLE_POLICY") < build.system_prompt.index("## CORE_IDENTITY")
    assert build.system_prompt.index("## CORE_IDENTITY") < build.system_prompt.index("## CONTEXT_MEMORY")

