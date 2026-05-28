from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t-rp-fit",
        user_id="u-rp-fit",
        core_direction="focus",
        phase="clarify",
        response_mode="practice",
    )


def test_writer_contract_exposes_answer_fit_related_planner_fields() -> None:
    contract = WriterContract(
        user_message="Дай один шаг прямо сейчас",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(has_relevant_knowledge=False),
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "give_direct_step",
            "answer_shape": "one_step",
            "response_depth": "short",
            "question_policy": "none",
            "practice_policy": "one_micro_step_allowed",
            "revoicing_policy": "suppressed",
            "continuity_policy": "continue_active_line",
            "safety_priority": False,
            "must_include": ["один конкретный шаг"],
            "must_avoid": ["без списка шагов"],
        },
    )

    ctx = contract.to_prompt_context()
    assert ctx["response_planner_next_move"] == "give_direct_step"
    assert ctx["response_planner_answer_shape"] == "one_step"
    assert ctx["response_planner_question_policy"] == "none"
    assert ctx["response_planner_practice_policy"] == "one_micro_step_allowed"
    assert "без списка шагов" in ctx["response_planner_must_avoid"]
