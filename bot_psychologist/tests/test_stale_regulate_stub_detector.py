from __future__ import annotations

from bot_agent.multiagent.stale_stub_detector import contains_stale_stub, detect_stale_stub


def test_detect_stale_stub_in_string() -> None:
    payload = detect_stale_stub(
        "Отвечу по сути без навязывания практик. Ключевой узел в том, что автоматический контроль может включать внутреннюю перегрузку."
    )
    assert payload["detected"] is True
    assert payload["matched_phrase"]


def test_detect_stale_stub_nested_payload() -> None:
    payload = {
        "answers": [
            "ok",
            {"final_answer": "Сфокусируюсь на разборе, без практик по умолчанию."},
        ]
    }
    detected = contains_stale_stub(payload)
    assert detected["detected"] is True

