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
        **kwargs,
    ):
        self.last_call = {
            "system_prompt": self.build_system_prompt(),
            "question": user_question,
            "blocks": blocks,
            "conversation_history": conversation_history,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        return {
            "answer": "test-answer",
            "model_used": model,
            "tokens_used": 123,
            "error": None,
        }


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
        user_level_adapter=object(),  # backward-compatible arg; ignored in Neo runtime
        additional_system_context="STATE_CONTEXT",
    )

    assert result["error"] is None
    assert result["mode"] == "INTERVENTION"
    assert "MODE DIRECTIVE" in answerer.last_call["system_prompt"]
    assert "INTERVENTION" in answerer.last_call["system_prompt"]
    assert "STATE_CONTEXT" in answerer.last_call["system_prompt"]
    assert "LEVEL_ADAPTER" not in answerer.last_call["system_prompt"]
    assert answerer.last_call["temperature"] < config.LLM_TEMPERATURE


def test_response_generator_mode_override_replaces_sd_layer() -> None:
    answerer = _DummyAnswerer()
    generator = ResponseGenerator(answerer=answerer)

    result = generator.generate(
        "Что такое нейросталкинг?",
        blocks=[object()],
        mode="PRESENCE",
        confidence_level="medium",
        mode_prompt_override="INFORMATIONAL MODE PROMPT",
        mode_overrides_sd=True,
    )

    assert result["error"] is None
    system_prompt = answerer.last_call["system_prompt"]
    assert "INFORMATIONAL MODE PROMPT" in system_prompt
    assert "MODE DIRECTIVE" not in system_prompt


def test_response_generator_forwards_session_store_params() -> None:
    answerer = _DummyAnswerer()
    generator = ResponseGenerator(answerer=answerer)
    dummy_store = object()

    generator.generate(
        "Тест",
        blocks=[object()],
        session_store=dummy_store,
        session_id="session-1",
    )

    assert answerer.last_call["session_store"] is dummy_store
    assert answerer.last_call["session_id"] == "session-1"

