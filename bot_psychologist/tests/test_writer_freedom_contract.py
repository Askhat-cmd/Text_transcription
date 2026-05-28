from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.philosophy_kernel import (
    PHILOSOPHY_KERNEL_VERSION,
    WRITER_FREEDOM_CONTRACT_VERSION,
    build_philosophy_kernel_runtime_payload,
)


def _thread_state() -> ThreadState:
    return ThreadState(
        thread_id="t-philo",
        user_id="u-philo",
        core_direction="identity",
        phase="clarify",
        response_mode="reflect",
    )


def test_writer_contract_serializes_new_fields() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Что такое нейросталкинг?",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    contract = WriterContract(
        user_message="test",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(),
        philosophy_kernel=payload,
        writer_freedom_contract=dict(payload.get("writer_freedom_contract", {})),
    )

    data = contract.to_dict()
    assert isinstance(data.get("philosophy_kernel"), dict)
    assert isinstance(data.get("writer_freedom_contract"), dict)
    assert data["philosophy_kernel"]["kernel_version"] == PHILOSOPHY_KERNEL_VERSION
    assert data["writer_freedom_contract"]["version"] == WRITER_FREEDOM_CONTRACT_VERSION


def test_writer_contract_backward_compatibility_without_new_fields() -> None:
    contract = WriterContract(
        user_message="hello",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(),
    )
    ctx = contract.to_prompt_context()
    assert ctx["philosophy_kernel"] == {}
    assert ctx["writer_freedom_contract"] == {}
    assert ctx["mode_is_hint_not_cage"] is True
    assert ctx["practice_requires_gate"] is True
    assert ctx["writer_freedom_hard_boundaries"] == []


def test_writer_freedom_fields_propagate_to_prompt_context() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Мне кажется я недостаточен и не справлюсь",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    contract = WriterContract(
        user_message="test",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(),
        philosophy_kernel=payload,
    )
    ctx = contract.to_prompt_context()
    assert ctx["mode_is_hint_not_cage"] is True
    assert ctx["practice_requires_gate"] is True
    assert "no_unsolicited_practice" in ctx["writer_freedom_hard_boundaries"]
    assert ctx["writer_question_limit"] == 1
    assert "imperfect_self_program" in ctx["philosophy_kernel_selected_lenses"]


def test_known_concept_and_kernel_lens_do_not_force_practice() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Что такое нейросталкинг?",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    contract = WriterContract(
        user_message="что такое нейросталкинг",
        thread_state=_thread_state(),
        memory_bundle=MemoryBundle(),
        philosophy_kernel=payload,
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "should_answer_directly": True,
            },
            "practice_gate": {"practice_allowed": False},
        },
    )
    ctx = contract.to_prompt_context()
    assert ctx["practice_ban_enforced"] is True
    assert ctx["practice_requires_gate"] is True
    assert ctx["known_concept_clarification_ban"] is True
    assert "neurostalking" in ctx["philosophy_kernel_selected_lenses"]

