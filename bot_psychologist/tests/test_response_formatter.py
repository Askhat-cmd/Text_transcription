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


def test_formatter_does_not_clip_neo_answer() -> None:
    formatter = ResponseFormatter(mode_char_limits={"PRESENCE": 4000})
    answer = (
        "Сначала коротко отражаю твое состояние. "
        "Затем объясняю механизм, почему тревога усиливается перед встречей. "
        "Дальше даю 2-3 практики, которые можно применить прямо сейчас. "
        "И в конце предлагаю мягкий следующий шаг на сегодня."
    )
    text = formatter.format_answer(
        answer,
        mode="PRESENCE",
        confidence_level="high",
        informational_mode=True,
    )
    assert text == answer


def test_calculate_target_length_short_validation() -> None:
    formatter = ResponseFormatter()
    target = formatter.calculate_target_length(
        user_message="мне плохо",
        routing_mode="VALIDATION",
        sd_level="GREEN",
    )
    assert target["max_sentences"] == 2


def test_calculate_target_length_long_thinking() -> None:
    formatter = ResponseFormatter()
    target = formatter.calculate_target_length(
        user_message=" ".join(["слово"] * 25),
        routing_mode="THINKING",
        sd_level="YELLOW",
    )
    assert target["max_sentences"] == 6


def test_formatter_applies_sentence_cap_from_user_message() -> None:
    formatter = ResponseFormatter(mode_char_limits={"VALIDATION": 2000})
    text = formatter.format_answer(
        "Первое. Второе. Третье. Четвертое.",
        mode="VALIDATION",
        confidence_level="high",
        user_message="коротко",
        sd_level="GREEN",
    )
    # VALIDATION + short message => максимум 2 предложения.
    assert text.count(".") <= 2


def test_formatter_skips_sentence_cap_for_informational_mode() -> None:
    formatter = ResponseFormatter(mode_char_limits={"PRESENCE": 2000})
    text = formatter.format_answer(
        "Первое. Второе. Третье. Четвертое.",
        mode="PRESENCE",
        confidence_level="high",
        user_message="коротко",
        sd_level="GREEN",
        informational_mode=True,
    )
    assert text.count(".") >= 3
