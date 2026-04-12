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

def test_formatter_does_not_apply_sentence_cap_without_explicit_brevity() -> None:
    formatter = ResponseFormatter(mode_char_limits={"VALIDATION": 4000})
    source = "First sentence. Second sentence. Third sentence. Fourth sentence."
    text = formatter.format_answer(
        source,
        mode="VALIDATION",
        confidence_level="high",
        user_message="I feel anxious before a meeting",
        sd_level="GREEN",
    )
    assert text == source


def test_formatter_does_not_clip_regular_answer_by_mode_limit() -> None:
    formatter = ResponseFormatter(mode_char_limits={"PRESENCE": 200})
    source = (
        "Первый абзац с объяснением контекста. "
        "Второй абзац с уточнением механизма и причин. "
        "Третий абзац с практическим применением в реальной ситуации. "
        "Четвертый абзац с понятным и выполнимым следующим шагом."
    )
    text = formatter.format_answer(
        source,
        mode="PRESENCE",
        confidence_level="high",
        user_message="Расскажи подробно, пожалуйста",
        sd_level="GREEN",
        informational_mode=False,
    )
    assert text == source


def test_formatter_applies_hard_cap_for_extreme_output() -> None:
    formatter = ResponseFormatter(mode_char_limits={"PRESENCE": 2000}, hard_max_chars=120)
    source = "Очень длинный текст. " * 20
    text = formatter.format_answer(
        source,
        mode="PRESENCE",
        confidence_level="high",
        user_message="Расскажи подробно",
        sd_level="GREEN",
    )
    assert len(text) <= 120
    assert text.endswith("...")
