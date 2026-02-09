#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for unified response generator."""

from bot_agent.config import config
from bot_agent.response import ResponseGenerator


class _DummyAnswerer:
    def __init__(self) -> None:
        self.last_call = {}

    def build_system_prompt(self) -> str:
        return "BASE_SYSTEM_PROMPT"

    def generate_answer(
        self,
        user_question,
        blocks,
        conversation_history=None,
        model=None,
        temperature=None,
        max_tokens=None,
    ):
        self.last_call = {
            "system_prompt": self.build_system_prompt(),
            "question": user_question,
            "blocks": blocks,
            "conversation_history": conversation_history,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return {
            "answer": "test-answer",
            "model_used": model,
            "tokens_used": 123,
            "error": None,
        }


class _DummyLevelAdapter:
    @staticmethod
    def adapt_system_prompt(prompt: str) -> str:
        return prompt + "\nLEVEL_ADAPTER"


def test_response_generator_builds_mode_directive_and_context() -> None:
    answerer = _DummyAnswerer()
    generator = ResponseGenerator(answerer=answerer)

    result = generator.generate(
        "Как начать?",
        blocks=[object()],
        conversation_context="short context",
        mode="INTERVENTION",
        confidence_level="low",
        forbid=["lecture"],
        user_level_adapter=_DummyLevelAdapter(),
        additional_system_context="STATE_CONTEXT",
    )

    assert result["error"] is None
    assert result["mode"] == "INTERVENTION"
    assert "MODE DIRECTIVE" in answerer.last_call["system_prompt"]
    assert "INTERVENTION" in answerer.last_call["system_prompt"]
    assert "STATE_CONTEXT" in answerer.last_call["system_prompt"]
    assert "LEVEL_ADAPTER" in answerer.last_call["system_prompt"]
    assert answerer.last_call["temperature"] < config.LLM_TEMPERATURE

