from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.prompt_registry_v2 import prompt_registry_v2


def test_prompt_registry_removes_snapshot_block_from_memory_context() -> None:
    conversation_context = (
        "SUMMARY:\nкоротко\n\n"
        "SNAPSHOT:\n"
        "- nervous_system_state: window\n"
        "- request_function: understand\n\n"
        "RECENT DIALOG:\n- user: мне тревожно\n"
    )
    build = prompt_registry_v2.build(
        query="мне тревожно",
        blocks=[],
        conversation_context=conversation_context,
        additional_system_context="",
        route="reflect",
        mode="THINKING",
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "hyper",
            "request_function": "understand",
            "core_theme": "anxiety",
        },
    )
    reflective = build.sections["REFLECTIVE_METHOD"]
    assert "SNAPSHOT:" not in reflective
    assert "nervous_system_state: window" not in reflective


def test_prompt_registry_single_nervous_state_value() -> None:
    build = prompt_registry_v2.build(
        query="мне тревожно",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="reflect",
        mode="THINKING",
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "hyper",
            "request_function": "understand",
            "core_theme": "anxiety",
        },
    )
    values = set(re.findall(r"nervous_system_state[:\s]+(\w+)", build.system_prompt.lower()))
    assert values == {"hyper"}
