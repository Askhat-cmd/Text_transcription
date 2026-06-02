from __future__ import annotations

from bot_agent.multiagent.stale_stub_detector import contains_stale_stub, detect_stale_stub


def test_detector_catches_exact_bad_phrase() -> None:
    payload = detect_stale_stub(
        "Отвечу по сути без навязывания практик. Ключевой узел в том, что автоматический контроль может включать внутреннюю перегрузку еще до действия."
    )
    assert payload["detected"] is True
    assert payload["detector_kind"] in {"exact", "semantic"}


def test_detector_catches_semantic_variant() -> None:
    payload = detect_stale_stub(
        "Проблема в том, что автоматический контроль до действия может запускать внутреннюю перегрузку и сужать выбор."
    )
    assert payload["detected"] is True
    assert payload["detector_kind"] == "semantic"


def test_recursive_detector_scans_all_nested_turn_answers() -> None:
    nested = {
        "case_results": [
            {"answer": "ок"},
            {"answer": "Сфокусируюсь на разборе, без практик по умолчанию."},
        ]
    }
    payload = contains_stale_stub(nested)
    assert payload["detected"] is True
    assert payload["matched_path"] in {"case_results", "1", "answer"}
