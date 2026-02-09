#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DecisionGate composition logic."""

from bot_agent.decision import DecisionGate
from bot_agent.retrieval import StageFilter


def test_decision_gate_routes_to_intervention_when_allowed() -> None:
    gate = DecisionGate()
    result = gate.route(
        signals={
            "local_similarity": 0.8,
            "voyage_confidence": 0.85,
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
    assert result.adjusted_by_stage is False
    assert result.confidence_level in {"medium", "high"}


def test_decision_gate_falls_back_when_stage_disallows() -> None:
    stage_filter = StageFilter(
        allowed_by_stage={
            "exploration": ["PRESENCE", "CLARIFICATION", "VALIDATION", "THINKING"],
            "surface": ["PRESENCE", "CLARIFICATION", "VALIDATION"],
            "awareness": ["PRESENCE", "CLARIFICATION", "VALIDATION", "THINKING"],
            "integration": ["PRESENCE", "CLARIFICATION", "VALIDATION", "THINKING", "INTEGRATION"],
        }
    )
    gate = DecisionGate(stage_filter=stage_filter)
    result = gate.route(
        signals={
            "local_similarity": 0.8,
            "voyage_confidence": 0.9,
            "delta_top1_top2": 0.8,
            "state_match": 0.8,
            "question_clarity": 0.8,
            "explicit_ask": True,
            "ask_type": "action",
            "intervention_cooldown_ok": True,
        },
        user_stage="exploration",
    )

    assert result.mode == "CLARIFICATION"
    assert result.adjusted_by_stage is True
