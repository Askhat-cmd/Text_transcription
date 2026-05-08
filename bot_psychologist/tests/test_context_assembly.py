from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.context_assembly import (
    MICRO_SUMMARY_MAX_CHARS,
    build_context_assembly_package_v1,
)
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        pattern_core="stable pattern core",
        active_frame={
            "current_need": "short support without pressure",
            "next_recommended_direction": "keep answer short and low pressure",
        },
    )


def test_context_assembly_short_turns_stay_full() -> None:
    bundle = MemoryBundle(
        recent_turns=[
            {"turn_index": 1, "user_input": "короткий вопрос", "bot_response": "короткий ответ"},
            {"turn_index": 2, "user_input": "еще вопрос", "bot_response": "еще ответ"},
        ],
        semantic_memory_hits=[],
        knowledge_rag_hits=[],
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=bundle,
    )

    assert len(package.recent_turns_full) == 4
    assert len(package.recent_turns_summarized) == 0
    assert package.trace.dropped_count == 0
    assert package.trace.version == "context_assembly_trace_v1"


def test_context_assembly_long_turn_becomes_micro_summary() -> None:
    long_text = " ".join(["длинный фрагмент"] * 120)
    bundle = MemoryBundle(
        recent_turns=[
            {"turn_index": 1, "user_input": long_text, "bot_response": "ок"},
        ],
        semantic_memory_hits=[],
        knowledge_rag_hits=[],
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=bundle,
    )

    assert len(package.recent_turns_summarized) == 1
    summary = package.recent_turns_summarized[0]
    assert summary.summary_method == "deterministic_extractive_v1"
    assert summary.was_truncated is True
    assert summary.raw_chars > summary.summary_chars
    assert summary.summary_chars <= MICRO_SUMMARY_MAX_CHARS


def test_context_assembly_dedup_and_budget_limit() -> None:
    repeated = "повторяющийся текст контекста"
    bundle = MemoryBundle(
        recent_turns=[
            {"turn_index": 1, "user_input": repeated, "bot_response": "ok"},
        ],
        semantic_memory_hits=[
            {"turn_id": "turn_99", "source": "semantic_memory", "score": 0.9, "content": repeated},
            {"turn_id": "turn_98", "source": "semantic_memory", "score": 0.8, "content": "уникальный semantic"},
        ],
        knowledge_rag_hits=[
            {"chunk_id": "k1", "source": "kb", "score": 0.9, "content": repeated},
            {"chunk_id": "k2", "source": "kb", "score": 0.7, "content": "очень длинный " * 80},
        ],
        personal_history_context=[{"source": "conversation_summary", "content": "summary"}],
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=bundle,
        max_context_chars=450,
    )

    assert package.trace.duplicates_removed >= 2
    assert package.context_budget.used_chars <= package.context_budget.max_chars
    assert "budget_limit" in package.trace.reasons


def test_context_assembly_package_serialization_roundtrip() -> None:
    bundle = MemoryBundle(
        recent_turns=[{"turn_index": 1, "user_input": "u", "bot_response": "a"}],
        personal_history_context=[{"source": "summary", "content": "x"}],
        semantic_memory_hits=[{"turn_id": "turn_1", "source": "semantic_memory", "score": 0.8, "content": "s"}],
        knowledge_rag_hits=[{"chunk_id": "c1", "source": "kb", "score": 0.9, "content": "k"}],
    )
    package = build_context_assembly_package_v1(
        user_message="сообщение",
        thread_state=_thread(),
        memory_bundle=bundle,
    )

    restored = type(package).from_dict(package.to_dict())
    assert restored.to_dict() == package.to_dict()
