from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent_constants import (
    _contains_any,
    _extract_literal_markdown_echo_request,
    _to_float,
    _to_int,
)


def test_extract_literal_markdown_echo_request_returns_empty_for_blank_input() -> None:
    assert _extract_literal_markdown_echo_request("") == ""
    assert _extract_literal_markdown_echo_request(None) == ""


def test_extract_literal_markdown_echo_request_returns_markdown_candidate() -> None:
    message = "Верни без объяснений и без изменений следующий markdown-блок:\n- пункт 1\n- пункт 2"
    assert _extract_literal_markdown_echo_request(message) == "- пункт 1\n- пункт 2"


def test_to_int_returns_default_on_invalid_input() -> None:
    assert _to_int("42", 7) == 42
    assert _to_int("not-a-number", 7) == 7
    assert _to_int(None, 7) == 7


def test_to_float_returns_default_on_invalid_input() -> None:
    assert _to_float("3.5", 1.25) == 3.5
    assert _to_float("bad", 1.25) == 1.25
    assert _to_float(None, 1.25) == 1.25


def test_contains_any_matches_case_insensitively() -> None:
    assert _contains_any("Нужен спокойный ВДОХ сейчас", ("вдох", "выдох")) is True
    assert _contains_any("Просто текст", ("вдох", "выдох")) is False
    assert _contains_any(None, ("вдох", "выдох")) is False
