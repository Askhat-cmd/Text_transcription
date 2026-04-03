from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_prompt_style_policy_inform_rich() -> None:
    build = prompt_registry_v2.build(
        query="Что такое самоосознание?",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={"interaction_mode": "informational"},
    )
    style = build.sections["A_STYLE_POLICY"].lower()
    assert "2-4" in style
    assert "практический смысл" in style
    assert "сухого faq" in style
