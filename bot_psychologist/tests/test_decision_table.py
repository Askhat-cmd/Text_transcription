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


def test_decision_table_stage_filter_blocks_deep_intervention() -> None:
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
