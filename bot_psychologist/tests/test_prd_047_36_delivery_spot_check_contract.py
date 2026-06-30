from __future__ import annotations

import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from tools import prd_047_36_owner_pilot_readiness_gate_lib as gate


def test_delivery_spot_check_detects_writer_raw_vs_api_mismatch() -> None:
    result = gate.build_delivery_spot_check(
        writer_raw_answer="Полный ответ без обрезки.",
        api_answer="Обрезанный ответ.",
        memory_answer="Обрезанный ответ.",
        visible_chat_answer=None,
        validator_blocked=False,
        acceptance_retry_attempted=False,
    )
    payload = result["delivery_spot_check_v1"]
    assert payload["strict_raw_compare"] is True
    assert payload["blocker"] is True
    assert "writer_raw_vs_api_mismatch" in payload["blocker_reasons"]


def test_delivery_spot_check_ignores_raw_compare_when_retry_happened() -> None:
    result = gate.build_delivery_spot_check(
        writer_raw_answer="Черновой первый ответ.",
        api_answer="Переписанный финальный ответ.",
        memory_answer="Переписанный финальный ответ.",
        visible_chat_answer=None,
        validator_blocked=False,
        acceptance_retry_attempted=True,
    )
    payload = result["delivery_spot_check_v1"]
    assert payload["strict_raw_compare"] is False
    assert payload["blocker"] is False
    assert payload["api_vs_memory_match"] is True


def test_delivery_spot_check_exposes_quarantine_context_for_memory_gap() -> None:
    result = gate.build_delivery_spot_check(
        writer_raw_answer="Стих на второй ход.",
        api_answer="Стих на второй ход.",
        memory_answer="Прошлый прозаичный ответ.",
        visible_chat_answer=None,
        validator_blocked=False,
        acceptance_retry_attempted=False,
        acceptance_gate_status="failed",
        must_quarantine_answer=True,
        quarantine_reason="answer_does_not_address_direct_question",
    )
    payload = result["delivery_spot_check_v1"]
    assert payload["blocker"] is True
    assert payload["acceptance_gate_status"] == "failed"
    assert payload["must_quarantine_answer"] is True
    assert payload["quarantine_reason"] == "answer_does_not_address_direct_question"
    assert payload["quarantine_explains_memory_gap"] is True
