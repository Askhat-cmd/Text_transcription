#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for SD pipeline pieces."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bot_agent.response.response_generator import ResponseGenerator
from bot_agent.sd_classifier import SDClassificationResult, SDClassifier, sd_compatibility_resolver


@dataclass
class _DummyBlock:
    block_id: str = "b1"
    title: str = "dummy"
    metadata: dict | None = None


class _DummyAnswerer:
    def __init__(self) -> None:
        self.last_system_prompt = ""

    def build_system_prompt(self) -> str:
        return "BASE_SYSTEM_PROMPT"

    def generate_answer(self, user_question, blocks, **kwargs):
        self.last_system_prompt = self.build_system_prompt()
        prompt = self.last_system_prompt
        if "SD-адаптация: BLUE" in prompt:
            answer = "Шаг 1: зафиксируй правило. Шаг 2: выполни действие по плану."
        elif "SD-адаптация: GREEN" in prompt:
            answer = "Я слышу, что тебе сейчас непросто. Это важно."
        elif "SD-адаптация: YELLOW" in prompt:
            answer = "Замечаю паттерн и контекст того, как система реагирует."
        else:
            answer = "Нейтральный ответ."
        return {"answer": answer, "tokens_used": 10, "error": None}


def _classifier() -> SDClassifier:
    return SDClassifier()


def test_sd_red_integration() -> None:
    message = "Все достали, никто не уважает меня"
    sd_result = _classifier()._heuristic_classify(message)
    assert sd_result.primary == "RED"
    assert "GREEN" not in sd_result.allowed_blocks
    response_metadata = {"sd_allowed_blocks": sd_result.allowed_blocks}
    assert "YELLOW" not in response_metadata["sd_allowed_blocks"]


def test_sd_blue_response_is_structured() -> None:
    message = "Я должна была этого не делать, чувствую вину перед семьёй"
    sd_result = _classifier()._heuristic_classify(message)
    assert sd_result.primary == "BLUE"

    generator = ResponseGenerator(answerer=_DummyAnswerer())
    result = generator.generate(
        query=message,
        blocks=[_DummyBlock()],
        mode="CLARIFICATION",
        confidence_level="medium",
        sd_level=sd_result.primary,
    )
    response = result["answer"].lower()
    assert not response.startswith("теория")
    assert ("шаг" in response) or ("план" in response)


def test_sd_green_response_validates_feelings() -> None:
    message = "Не могу справиться с тревогой, хочу понять что чувствую"
    sd_result = _classifier()._heuristic_classify(message)
    assert sd_result.primary == "GREEN"
    assert "GREEN" in sd_result.allowed_blocks

    generator = ResponseGenerator(answerer=_DummyAnswerer())
    result = generator.generate(
        query=message,
        blocks=[_DummyBlock()],
        mode="VALIDATION",
        confidence_level="medium",
        sd_level=sd_result.primary,
    )
    assert "слышу" in result["answer"].lower() or "важно" in result["answer"].lower()


def test_sd_yellow_allows_turquoise() -> None:
    message = "Замечаю паттерн - каждый раз в стрессе реагирую одинаково"
    sd_result = _classifier()._heuristic_classify(message)
    assert sd_result.primary == "YELLOW"
    assert "TURQUOISE" in sd_result.allowed_blocks


def test_sd_safety_no_high_levels_for_low_state() -> None:
    # Критический сценарий: вручную фиксируем низкий уровень как в PRD.
    allowed_blocks = sd_compatibility_resolver.get_allowed_levels(
        sd_level="PURPLE",
        user_state="crisis",
    )
    assert "YELLOW" not in allowed_blocks
    assert "TURQUOISE" not in allowed_blocks


def test_sd_crisis_orange_switches_to_blue_support() -> None:
    allowed_blocks = sd_compatibility_resolver.get_allowed_levels(
        sd_level="ORANGE",
        user_state="overwhelmed",
    )
    assert allowed_blocks == ["BLUE", "ORANGE"]


def test_sd_fallback_on_llm_error_and_response_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = _classifier()

    class _FailingCompletions:
        @staticmethod
        def create(*args, **kwargs):
            raise RuntimeError("forced llm fail")

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

    sd_result = classifier.classify("Мне страшно, всё плохо, не знаю что делать")
    assert sd_result.primary == "GREEN"
    assert sd_result.method == "fallback"

    generator = ResponseGenerator(answerer=_DummyAnswerer())
    result = generator.generate(
        query="Мне страшно, всё плохо, не знаю что делать",
        blocks=[_DummyBlock()],
        sd_level=sd_result.primary,
    )
    assert result["error"] is None
    assert result["answer"]
