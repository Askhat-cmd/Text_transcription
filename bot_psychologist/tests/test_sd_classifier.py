#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for SD classifier."""

import pytest

from bot_agent.sd_classifier import SDClassifier, SDClassificationResult


@pytest.mark.parametrize(
    "message, expected_level",
    [
        ("Мне страшно умереть, не могу дышать, физически плохо", "BEIGE"),
        ("Это чистое выживание, теряю сознание и не могу дышать", "BEIGE"),
        ("У нас в семье так принято, предки и судьба важнее", "PURPLE"),
        ("Боюсь сглазить, нужен ритуал и поддержка семьи", "PURPLE"),
        ("Все достали, не буду терпеть, хочу уважения", "RED"),
        ("Они меня не уважают, должны мне, я хочу действовать", "RED"),
        ("Я должна была так не делать, чувствую вину и долг", "BLUE"),
        ("Как положено, дисциплина важна, так нельзя нарушать", "BLUE"),
        ("Нужен результат и эффективность, какая выгода и цель", "ORANGE"),
        ("Хочу стратегию для карьеры: что это даст и как эффективно", "ORANGE"),
        ("Не могу справиться с тревогой, хочу понять что чувствую", "GREEN"),
        ("Нужна поддержка и эмпатия, важно чувствую связь", "GREEN"),
        ("Замечаю паттерн, хочу увидеть контекст и систему", "YELLOW"),
        ("Это метанаблюдение и интеграция: замечаю что я повторяюсь", "YELLOW"),
        ("Чувствую единство, всё одно, это про целостность бытия", "TURQUOISE"),
        ("Трансцендентность и планетарное единство дают ощущение целостности", "TURQUOISE"),
    ],
)
def test_heuristic_clean_cases(message: str, expected_level: str) -> None:
    classifier = SDClassifier()
    result = classifier._heuristic_classify(message)
    assert result.primary == expected_level
    assert result.method == "heuristic"


@pytest.mark.parametrize(
    "message, expected_primary",
    [
        ("У нас в семье так принято, но я хочу другого - не знаю кого слушать", "PURPLE"),
        # "Хочу наказать" (RED) + "по правилам нельзя" (BLUE) → BLUE перевешивает
        ("Хочу наказать, но понимаю что по правилам так нельзя", "BLUE"),
        ("Я всегда делал как положено, но результата нет и это неэффективно", "ORANGE"),
        ("Есть карьера и результат, но эффективность падает, хочу понять почему", "ORANGE"),
        ("Чувствую тревогу, но замечаю паттерн и контекст реакции", "YELLOW"),
    ],
)
def test_heuristic_boundary_cases(message: str, expected_primary: str) -> None:
    classifier = SDClassifier()
    result = classifier._heuristic_classify(message)
    assert result.primary == expected_primary
    assert result.method == "heuristic"


def test_llm_error_fallback_to_green(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = SDClassifier()

    class _FailingCompletions:
        @staticmethod
        def create(*args, **kwargs):
            raise RuntimeError("forced llm failure")

    class _FailingChat:
        completions = _FailingCompletions()

    class _FailingClient:
        chat = _FailingChat()

    classifier.client = _FailingClient()

    monkeypatch.setattr(
        classifier,
        "_heuristic_classify",
        lambda message, history=None: SDClassificationResult(
            primary="GREEN",
            secondary=None,
            confidence=0.10,
            indicator="forced_low_conf",
            method="heuristic",
        ),
    )

    result = classifier.classify("абсолютно неоднозначное сообщение")
    assert result.primary == "GREEN"
    assert result.method == "fallback"


def test_heuristic_not_red_intellectual_search() -> None:
    """Проверка что интеллектуальный поиск НЕ определяет RED."""
    classifier = SDClassifier()
    
    # Эти фразы должны быть GREEN/YELLOW, НЕ RED
    not_red_phrases = [
        ("хочу разобраться в нейросталкинге", ["GREEN", "YELLOW", "ORANGE"]),
        ("хочу понять себя", ["GREEN", "YELLOW"]),
        ("хочу изучить тему глубже", ["GREEN", "YELLOW", "ORANGE"]),
        ("интересно узнать больше", ["GREEN", "YELLOW"]),
        ("объясни как это работает", ["GREEN", "ORANGE"]),
    ]
    
    for phrase, allowed_levels in not_red_phrases:
        result = classifier._heuristic_classify(phrase)
        assert result.primary in allowed_levels, f"'{phrase}' → {result.primary} (expected one of {allowed_levels})"
        assert result.primary != "RED", f"'{phrase}' ложно определён как RED"


def test_heuristic_red_aggression_markers() -> None:
    """Проверка что RED определяется только по агрессии/доминированию."""
    classifier = SDClassifier()
    
    # Эти фразы должны быть RED
    red_phrases = [
        "меня все бесит",
        "ненавижу когда так делают",
        "все должны мне",
        "хочу прямо сейчас и немедленно",
        "никто не понимает меня",
    ]
    
    for phrase in red_phrases:
        result = classifier._heuristic_classify(phrase)
        assert result.primary == "RED", f"'{phrase}' → {result.primary} (expected RED)"
