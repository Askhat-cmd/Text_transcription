from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.context_package import (
    ContextAssemblyPackage,
    ContextAssemblyTrace,
    ContextBudget,
    TurnContextItem,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        pattern_core="stable core",
        active_frame={"current_need": "warm contact and validation"},
    )


def _context_package() -> ContextAssemblyPackage:
    return ContextAssemblyPackage(
        current_user_message="текущее сообщение",
        recent_turns_full=[
            TurnContextItem(
                turn_id="turn_1_user",
                role="user",
                content="первое сообщение",
                raw_chars=16,
                source="recent_full",
            )
        ],
        recent_turns_summarized=[],
        pattern_core="stable core",
        active_frame={"current_need": "warm contact and validation"},
        personal_history_context=[{"source": "summary", "content": "помнит про тревогу"}],
        semantic_memory_hits=[{"turn_id": "turn_3", "source": "semantic_memory", "score": 0.8, "content": "семантика"}],
        knowledge_rag_hits=[{"chunk_id": "k1", "source": "kb", "score": 0.9, "content": "знание"}],
        context_budget=ContextBudget(
            max_chars=8000,
            used_chars=210,
            full_turns=1,
            summarized_turns=0,
            dropped_turns=0,
            semantic_hits=1,
            knowledge_hits=1,
        ),
        trace=ContextAssemblyTrace(
            version="context_assembly_trace_v1",
            recent_full_count=1,
            summarized_count=0,
            dropped_count=0,
            semantic_hits_count=1,
            knowledge_hits_count=1,
            duplicates_removed=0,
            budget_used_chars=210,
            budget_limit_chars=8000,
            reasons=[],
        ),
    )


def test_writer_contract_uses_context_package_for_prompt_context() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy context"),
        context_package=_context_package(),
    )

    ctx = contract.to_prompt_context()

    assert "RECENT FULL TURNS" in ctx["conversation_context"]
    assert "legacy context" not in ctx["conversation_context"]
    assert isinstance(ctx["context_assembly_trace"], dict)
    assert ctx["context_assembly_trace"]["version"] == "context_assembly_trace_v1"
    assert ctx["semantic_hits"] == ["знание"]


def test_writer_contract_keeps_backward_compat_without_context_package() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy context"),
    )

    ctx = contract.to_prompt_context()

    assert ctx["conversation_context"] == "legacy context"
    assert ctx["context_assembly_trace"] == {}
    payload = contract.to_dict()
    assert payload["context_package"] is None
