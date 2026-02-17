#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for response formatter."""

from bot_agent.response import ResponseFormatter, format_mode_aware_response


def test_formatter_adds_question_for_clarification_mode() -> None:
    formatter = ResponseFormatter()
    text = formatter.format_answer(
        "Давайте немного уточним запрос",
        mode="CLARIFICATION",
        confidence_level="medium",
    )
    assert "?" in text


def test_formatter_adds_low_confidence_prefix() -> None:
    text = format_mode_aware_response(
        "Нужно понять, что именно сейчас мешает.",
        mode="PRESENCE",
        confidence_level="low",
    )
    assert text.lower().startswith("могу ошибаться")


def test_formatter_clips_long_answer() -> None:
    formatter = ResponseFormatter(mode_char_limits={"PRESENCE": 40})
    text = formatter.format_answer(
        "Это очень длинный ответ, который должен быть обрезан лимитом символов.",
        mode="PRESENCE",
        confidence_level="high",
    )
    assert len(text) <= 40
    assert text.endswith("...")

