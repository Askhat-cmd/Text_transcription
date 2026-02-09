#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for WorkingState model."""

from bot_agent.working_state import WorkingState


def test_working_state_stage_mapping() -> None:
    state = WorkingState(
        dominant_state="тревога",
        emotion="страх",
        phase="работа",
    )
    assert state.get_user_stage() == "exploration"


def test_working_state_serialization_roundtrip() -> None:
    original = WorkingState(
        dominant_state="эмоциональное онемение",
        emotion="пустота",
        defense="избегание",
        phase="интеграция",
        direction="действие",
        last_updated_turn=14,
        confidence_level="high",
    )

    restored = WorkingState.from_dict(original.to_dict())
    assert restored == original
