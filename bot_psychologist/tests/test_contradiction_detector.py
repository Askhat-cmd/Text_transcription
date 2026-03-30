#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for contradiction detector."""

from bot_agent.contradiction_detector import detect_contradiction


def test_detect_contradiction_positive_plus_anxiety() -> None:
    result = detect_contradiction("Всё нормально, просто немного устал и раздражаюсь")
    assert result["has_contradiction"] is True
    assert result["declared"] is not None
    assert result["actual_signal"] is not None
    assert "напряж" in result["suggestion"].lower()


def test_detect_contradiction_false_for_open_distress() -> None:
    result = detect_contradiction("Мне плохо, очень тяжело, не справляюсь")
    assert result["has_contradiction"] is False
    assert result["declared"] is None
    assert result["actual_signal"] is None
