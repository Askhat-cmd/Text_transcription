#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for mode prompt templates."""

from bot_agent.response import build_mode_prompt


def test_build_mode_prompt_contains_mode_and_confidence() -> None:
    prompt = build_mode_prompt("INTERVENTION", "high", ["lecture", "overload"])
    assert "РЕЖИМ: INTERVENTION" in prompt
    assert "Уверенность высокая" in prompt
    assert "lecture" in prompt


def test_build_mode_prompt_defaults_unknown_mode() -> None:
    prompt = build_mode_prompt("UNKNOWN", "low")
    assert "РЕЖИМ: UNKNOWN" in prompt
    assert "Уверенность низкая" in prompt
