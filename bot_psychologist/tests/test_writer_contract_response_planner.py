from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t-rp",
        user_id="u-rp",
        core_direction="focus",
        phase="clarify",
        response_mode="reflect",
    )


def test_writer_contract_prompt_context_has_response_planner_fields() -> None:
    contract = WriterContract(
        user_message="Хочу понять механизм",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(has_relevant_knowledge=False),
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "deepen_mechanism",
            "answer_shape": "mechanism_explanation",
            "response_depth": "medium",
            "target_micro_shift": "назвать механизм",
            "should_answer_directly": True,
            "question_policy": "none",
            "practice_policy": "forbidden",
            "revoicing_policy": "suppressed",
            "continuity_policy": "continue_active_line",
            "safety_priority": False,
            "must_include": ["связать с active_line"],
            "must_avoid": ["не предлагать практику"],
            "confidence": 0.83,
            "rationale": "mechanism intent path",
        },
    )
    ctx = contract.to_prompt_context()

    assert ctx["response_planner_version"] == "response_planner_v1"
    assert ctx["response_planner_enabled"] is True
    assert ctx["response_planner_next_move"] == "deepen_mechanism"
    assert ctx["response_planner_answer_shape"] == "mechanism_explanation"
    assert ctx["response_planner_question_policy"] == "none"
    assert ctx["response_planner_practice_policy"] == "forbidden"
    assert "не предлагать практику" in ctx["response_planner_must_avoid"]


def test_writer_contract_stays_backward_compatible_without_response_planner() -> None:
    contract = WriterContract(
        user_message="Привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(has_relevant_knowledge=False),
    )
    ctx = contract.to_prompt_context()

    assert ctx["response_planner_version"] == "response_planner_v1"
    assert ctx["response_planner_enabled"] is False
    assert ctx["response_planner_next_move"] == "continue_active_line"
    assert ctx["response_planner_practice_policy"] == "forbidden"
