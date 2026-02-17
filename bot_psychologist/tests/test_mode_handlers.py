#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for mode handlers."""

from bot_agent.decision import build_mode_directive


def test_build_mode_directive_populates_fields() -> None:
    directive = build_mode_directive(
        mode="CLARIFICATION",
        confidence_level="medium",
        reason="low confidence",
        forbid=["explain"],
    )
    assert directive.mode == "CLARIFICATION"
    assert directive.confidence_level == "medium"
    assert directive.reason == "low confidence"
    assert directive.forbid == ["explain"]
    assert "РЕЖИМ: CLARIFICATION" in directive.prompt
