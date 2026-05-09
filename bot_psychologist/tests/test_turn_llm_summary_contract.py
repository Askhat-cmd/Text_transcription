from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.turn_llm_summary import (
    TURN_LLM_SUMMARY_METHOD,
    TURN_LLM_SUMMARY_VERSION,
    TurnLLMSummary,
    validate_turn_llm_summary,
)


def _ready_payload(source_hash: str) -> TurnLLMSummary:
    return TurnLLMSummary(
        status="ready",
        summary="Пользователь обозначил тревогу и запрос на мягкий шаг.",
        important_quote="мне тревожно",
        open_loop="как начать разговор",
        user_need="поддержка перед разговором",
        assistant_move="предложен первый шаг",
        emotional_tone="напряженный",
        summary_version=TURN_LLM_SUMMARY_VERSION,
        summary_method=TURN_LLM_SUMMARY_METHOD,
        model="gpt-4o-mini",
        provider="mock",
        source_hash=source_hash,
        created_at="2026-05-09T00:00:00+00:00",
        error=None,
    )


def test_turn_llm_summary_contract_ready_valid_passes() -> None:
    record = _ready_payload("abc123")
    ok, reason = validate_turn_llm_summary(record, "abc123")
    assert ok is True
    assert reason == "ok"


def test_turn_llm_summary_contract_hash_mismatch_fails() -> None:
    record = _ready_payload("abc123")
    ok, reason = validate_turn_llm_summary(record, "zzz")
    assert ok is False
    assert reason == "source_hash_mismatch"


def test_turn_llm_summary_contract_pending_fails_for_context_use() -> None:
    record = _ready_payload("abc123")
    record.status = "pending"
    ok, reason = validate_turn_llm_summary(record, "abc123")
    assert ok is False
    assert reason == "pending"
