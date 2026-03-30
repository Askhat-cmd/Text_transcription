#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DecisionTable routing rules."""

from bot_agent.decision import DecisionTable


def test_decision_table_low_confidence() -> None:
    signals = {
        "confidence": 0.3,
        "emotion_load": "low",
        "contradiction": False,
    }

    result = DecisionTable.evaluate(signals)

    assert result.route == "CLARIFICATION"
    assert result.rule_id == 1
    assert "explain" in result.forbid


def test_decision_table_intervention_signal() -> None:
    signals = {
        "confidence": 0.65,
        "explicit_ask": True,
        "ask_type": "action",
        "user_stage": "exploration",
        "intervention_cooldown_ok": True,
    }

    result = DecisionTable.evaluate(signals)

    assert result.route == "INTERVENTION"
    assert result.rule_id == 3


def test_decision_table_blocks_deep_intervention_on_surface() -> None:
    signals = {
        "confidence": 0.8,
        "explicit_ask": True,
        "ask_type": "action",
        "user_stage": "surface",
    }

    result = DecisionTable.evaluate(signals)
    assert result.route == "CLARIFICATION"
    assert result.rule_id == 8
    assert "deep_intervention" in result.forbid


def test_decision_table_validation_first_for_new_emotional_topic() -> None:
    signals = {
        "confidence": 0.8,
        "is_first_response_on_topic": True,
        "has_emotional_signal": True,
        "current_turn_in_topic": 1,
        "validation_first_enabled": True,
        "insight_signal": False,
        "explicit_ask": True,
        "ask_type": "action",
        "user_stage": "exploration",
    }

    result = DecisionTable.evaluate(signals)
    assert result.route == "VALIDATION"
    assert result.rule_id == 100
