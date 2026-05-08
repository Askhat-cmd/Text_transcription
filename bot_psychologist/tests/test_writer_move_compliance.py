from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.diagnostic_card import DiagnosticCard
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.writer_move_compliance import (
    build_writer_move_compliance_trace_v1,
    build_writer_move_instructions_v1,
)


def _card(*, move: str, risk_flags: list[str] | None = None) -> DiagnosticCard:
    return DiagnosticCard(
        version="diagnostic_card_v1",
        situation_label="generic_support",
        user_state_summary="window/explore: openness=open, ok_position=I+W+",
        thread_line_summary="continuing active thread",
        current_need="gentle support",
        suggested_writer_move=move,
        avoid_list=[],
        confidence=0.8,
        risk_flags=list(risk_flags or []),
    )


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t1",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        response_mode="validate",
    )


def test_regulate_first_forbids_questions_when_low_resource() -> None:
    instructions = build_writer_move_instructions_v1(
        _card(move="regulate_first", risk_flags=["low_resource"])
    )
    assert instructions["max_questions"] == 0
    assert "do_not_ask_followup_question" in instructions["must_not_do"]


def test_practice_move_requires_one_micro_step() -> None:
    instructions = build_writer_move_instructions_v1(_card(move="offer_one_micro_step"))
    assert instructions["max_questions"] == 0
    assert "offer_one_executable_micro_step" in instructions["must_do"]
    assert "do_not_offer_list" in instructions["must_not_do"]


def test_semantic_continuation_reflect_pattern_once_constraints() -> None:
    instructions = build_writer_move_instructions_v1(_card(move="reflect_pattern_once"))
    assert instructions["max_questions"] == 1
    assert "name_one_repeated_pattern_gently" in instructions["must_do"]
    assert "do_not_list_multiple_hypotheses" in instructions["must_not_do"]


def test_compliance_trace_catches_question_violation() -> None:
    instructions = build_writer_move_instructions_v1(_card(move="regulate_first", risk_flags=["low_resource"]))
    trace = build_writer_move_compliance_trace_v1(
        final_answer="Сделай вдох. Как стало? Что хочется дальше?",
        instructions=instructions,
    )
    assert trace["max_questions"] == 0
    assert "too_many_questions" in trace["violations"]
    assert "regulate_should_not_ask_question" in trace["violations"]


def test_writer_contract_exposes_writer_move_instructions() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy"),
        diagnostic_card=_card(move="reflect_pattern_once"),
    )
    ctx = contract.to_prompt_context()
    assert ctx["writer_move_instructions"]["version"] == "writer_move_instructions_v1"
    assert ctx["writer_move_instructions"]["move"] == "reflect_pattern_once"


def test_writer_contract_default_instructions_without_diagnostic_card() -> None:
    contract = WriterContract(
        user_message="привет",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(conversation_context="legacy"),
    )
    ctx = contract.to_prompt_context()
    assert ctx["writer_move_instructions"]["version"] == "writer_move_instructions_v1"
    assert ctx["writer_move_instructions"]["move"] == "validate_briefly"
