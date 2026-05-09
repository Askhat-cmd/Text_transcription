from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.multiagent.context_assembly import build_context_assembly_package_v1
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.turn_summary_service import compute_turn_source_hash


def _thread() -> ThreadState:
    return ThreadState(
        thread_id="t-llm-summary",
        user_id="u1",
        core_direction="topic",
        phase="clarify",
        pattern_core="pattern",
        active_frame={"current_need": "support"},
    )


def _long_user_text() -> str:
    return ("Мне трудно и тревожно. " * 90).strip()


def _turn_with_summary(summary_payload: dict) -> dict:
    return {
        "turn_index": 1,
        "user_input": _long_user_text(),
        "bot_response": "Я рядом. Давай выберем один мягкий шаг.",
        "turn_llm_summary": summary_payload,
    }


def test_context_assembly_pending_summary_falls_back_to_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_USE_IN_CONTEXT", True)
    turn = _turn_with_summary(
        {
            "status": "pending",
            "summary": "",
            "summary_version": "turn_llm_summary_v1",
            "summary_method": "llm_abstractive_v1",
            "source_hash": compute_turn_source_hash(_long_user_text(), "Я рядом. Давай выберем один мягкий шаг."),
            "created_at": "2026-05-09T00:00:00+00:00",
        }
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(recent_turns=[turn]),
    )
    methods = {item.summary_method for item in package.recent_turns_summarized}
    assert "deterministic_extractive_v1" in methods
    assert "llm_summary_pending" in package.trace.reasons


def test_context_assembly_failed_summary_falls_back_to_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_USE_IN_CONTEXT", True)
    turn = _turn_with_summary(
        {
            "status": "failed",
            "summary": "",
            "summary_version": "turn_llm_summary_v1",
            "summary_method": "llm_abstractive_v1",
            "source_hash": compute_turn_source_hash(_long_user_text(), "Я рядом. Давай выберем один мягкий шаг."),
            "created_at": "2026-05-09T00:00:00+00:00",
            "error": "timeout",
        }
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(recent_turns=[turn]),
    )
    methods = {item.summary_method for item in package.recent_turns_summarized}
    assert "deterministic_extractive_v1" in methods
    assert "llm_summary_failed" in package.trace.reasons


def test_context_assembly_ready_summary_used(monkeypatch) -> None:
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_USE_IN_CONTEXT", True)
    source_hash = compute_turn_source_hash(_long_user_text(), "Я рядом. Давай выберем один мягкий шаг.")
    turn = _turn_with_summary(
        {
            "status": "ready",
            "summary": "Пользователь говорит о тревоге и трудности начать. Ассистент предложил мягкий первый шаг.",
            "important_quote": "Мне трудно и тревожно",
            "summary_version": "turn_llm_summary_v1",
            "summary_method": "llm_abstractive_v1",
            "source_hash": source_hash,
            "created_at": "2026-05-09T00:00:00+00:00",
        }
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(recent_turns=[turn]),
    )
    methods = {item.summary_method for item in package.recent_turns_summarized}
    assert "llm_abstractive_v1" in methods
    assert "llm_summary_ready_used" in package.trace.reasons


def test_context_assembly_ready_summary_hash_mismatch_fallback(monkeypatch) -> None:
    monkeypatch.setattr(config, "TURN_LLM_SUMMARY_USE_IN_CONTEXT", True)
    turn = _turn_with_summary(
        {
            "status": "ready",
            "summary": "Summary text",
            "summary_version": "turn_llm_summary_v1",
            "summary_method": "llm_abstractive_v1",
            "source_hash": "wrong_hash",
            "created_at": "2026-05-09T00:00:00+00:00",
        }
    )
    package = build_context_assembly_package_v1(
        user_message="новое сообщение",
        thread_state=_thread(),
        memory_bundle=MemoryBundle(recent_turns=[turn]),
    )
    methods = {item.summary_method for item in package.recent_turns_summarized}
    assert "deterministic_extractive_v1" in methods
    assert "llm_summary_source_hash_mismatch" in package.trace.reasons
