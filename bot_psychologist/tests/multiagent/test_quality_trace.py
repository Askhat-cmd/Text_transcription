from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.quality_trace import QUALITY_TRACE_VERSION, build_quality_trace


def _thread(*, response_mode: str = "reflect", continuity_score: float = 0.74) -> ThreadState:
    now = datetime.utcnow()
    thread = ThreadState(
        thread_id="thread-1",
        user_id="u1",
        core_direction="разобраться в реакции",
        phase="explore",  # type: ignore[arg-type]
        relation_to_thread="continue",  # type: ignore[arg-type]
        response_mode=response_mode,  # type: ignore[arg-type]
        continuity_score=continuity_score,
        turns_in_phase=2,
        open_loops=["обсудить страх ошибки"],
        closed_loops=["дыхание перед сном"],
        response_goal="дать один практический шаг" if response_mode == "practice" else "",
        created_at=now,
        updated_at=now,
    )
    thread.confidence = 0.81
    return thread


def _contract(*, response_mode: str = "reflect", context: str = "User: я боюсь ошибиться") -> WriterContract:
    memory = MemoryBundle(
        conversation_context=context,
        rag_query="страх ошибки",
        user_profile=UserProfile(patterns=["перфекционизм"], values=["осознанность"]),
        semantic_hits=[],
        has_relevant_knowledge=False,
        context_turns=3,
    )
    return WriterContract(
        user_message="Мне тревожно перед задачей",
        thread_state=_thread(response_mode=response_mode),
        memory_bundle=memory,
    )


def test_quality_trace_returns_dict_and_expected_top_keys() -> None:
    trace = build_quality_trace(
        final_answer="Я понимаю твое состояние. Давай посмотрим на один шаг.",
        writer_contract=_contract(),
        validation_result=ValidationResult(is_blocked=False),
    )
    assert isinstance(trace, dict)
    assert set(trace.keys()) == {
        "version",
        "answer",
        "state",
        "thread",
        "memory",
        "continuity",
        "response_mode",
        "writer_move_compliance",
        "validator",
        "summary_flags",
    }
    assert trace["version"] == QUALITY_TRACE_VERSION


def test_quality_trace_marks_questions_list_and_generic_risk() -> None:
    answer = "1) Что ты чувствуешь? 2) Что пугает? 3) Что важно? 4) Что попробуешь? Я понимаю."
    trace = build_quality_trace(
        final_answer=answer,
        writer_contract=_contract(),
        validation_result=ValidationResult(is_blocked=False),
    )
    assert trace["answer"]["too_many_questions"] is True
    assert trace["answer"]["contains_numbered_list"] is True
    assert trace["answer"]["generic_phrase_risk"] is True


def test_quality_trace_confidence_and_continuity_buckets() -> None:
    contract = _contract()
    contract.thread_state.continuity_score = 0.9
    contract.thread_state.confidence = 0.65

    trace = build_quality_trace(
        final_answer="Короткий, но по делу ответ.",
        writer_contract=contract,
        validation_result=ValidationResult(is_blocked=False),
    )

    assert trace["state"]["confidence_bucket"] == "medium"
    assert trace["thread"]["continuity_bucket"] == "high"


def test_quality_trace_practice_mode_flag_when_no_step() -> None:
    trace = build_quality_trace(
        final_answer="Держись, всё наладится.",
        writer_contract=_contract(response_mode="practice"),
        validation_result=ValidationResult(is_blocked=False),
    )
    assert "practice_without_step" in trace["response_mode"]["mode_risk_flags"]
    assert "practice_without_step" in trace["summary_flags"]


def test_quality_trace_contains_writer_move_compliance_trace() -> None:
    trace = build_quality_trace(
        final_answer="Сделай вдох. Как стало? Что дальше?",
        writer_contract=_contract(response_mode="validate"),
        validation_result=ValidationResult(is_blocked=False),
    )
    compliance = trace["writer_move_compliance"]
    assert compliance["version"] == "writer_move_compliance_trace_v1"
    assert isinstance(compliance["violations"], list)


def test_quality_trace_has_no_raw_user_text_or_raw_context() -> None:
    user_message = "Мой очень приватный текст"
    context = "User: мой приватный контекст"
    contract = _contract(context=context)
    contract.user_message = user_message

    trace = build_quality_trace(
        final_answer="Нейтральный ответ для проверки приватности.",
        writer_contract=contract,
        validation_result=ValidationResult(is_blocked=False, quality_flags=["too_short: 12 chars"]),
    )

    serialized = json.dumps(trace, ensure_ascii=False)
    assert user_message not in serialized
    assert context not in serialized
