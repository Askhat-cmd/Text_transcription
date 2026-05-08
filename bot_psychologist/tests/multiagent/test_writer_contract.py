from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def test_writer_contract_prompt_context_contains_semantic_fields() -> None:
    thread_state = ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        pattern_core="stable core",
        active_frame={
            "current_need": "short support without pressure",
            "next_recommended_direction": "keep answer short and low pressure",
        },
    )
    contract = WriterContract(
        user_message="hello",
        thread_state=thread_state,
        memory_bundle=MemoryBundle(),
    )

    context = contract.to_prompt_context()

    assert context["pattern_core"] == "stable core"
    assert isinstance(context["active_frame"], dict)
    assert context["active_frame"]["current_need"] == "short support without pressure"
