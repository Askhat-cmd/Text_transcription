#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DecisionGate composition logic."""

from bot_agent.decision import DecisionGate


def test_decision_gate_routes_to_intervention_when_allowed() -> None:
    gate = DecisionGate()
    result = gate.route(
        signals={
            "local_similarity": 0.8,
            "delta_top1_top2": 0.7,
            "state_match": 0.8,
            "question_clarity": 0.8,
            "explicit_ask": True,
            "ask_type": "action",
            "intervention_cooldown_ok": True,
        },
        user_stage="exploration",
    )

    assert result.mode == "INTERVENTION"
    assert result.track == "practice"
    assert result.tone == "empathic"
    assert result.confidence_level in {"medium", "high"}
