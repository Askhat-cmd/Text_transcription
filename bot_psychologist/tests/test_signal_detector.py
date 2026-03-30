#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for decision signal detector helpers."""

from types import SimpleNamespace

from bot_agent.decision import detect_routing_signals, resolve_user_stage
from bot_agent.working_state import WorkingState


def test_detect_routing_signals_explicit_action_ask() -> None:
    signals = detect_routing_signals(
        query="Но что мне делать дальше?",
        retrieved_blocks=[(object(), 0.82), (object(), 0.61)],
        state_analysis=None,
    )

    assert signals["explicit_ask"] is True
    assert signals["ask_type"] == "action"
    assert 0.0 <= signals["local_similarity"] <= 1.0
    assert 0.0 <= signals["delta_top1_top2"] <= 1.0


def test_detect_routing_signals_marks_first_emotional_topic() -> None:
    memory = SimpleNamespace(turns=[])
    signals = detect_routing_signals(
        query="Мне страшно и тревожно, не знаю что делать",
        retrieved_blocks=[(object(), 0.82), (object(), 0.61)],
        state_analysis=None,
        memory=memory,
    )
    assert signals["is_first_response_on_topic"] is True
    assert signals["current_turn_in_topic"] == 1
    assert signals["has_emotional_signal"] is True


def test_detect_routing_signals_not_first_topic_when_overlap() -> None:
    memory = SimpleNamespace(turns=[SimpleNamespace(user_input="Мне тревожно и страшно за будущее")])
    signals = detect_routing_signals(
        query="Все так же тревожно и страшно, хочу поддержки",
        retrieved_blocks=[(object(), 0.82), (object(), 0.61)],
        state_analysis=None,
        memory=memory,
    )
    assert signals["is_first_response_on_topic"] is False
    assert signals["current_turn_in_topic"] == 2


def test_resolve_user_stage_prefers_working_state() -> None:
    memory = SimpleNamespace(
        working_state=WorkingState(
            dominant_state="фрустрация",
            emotion="тревога",
            phase="работа",
        )
    )
    assert resolve_user_stage(memory) == "exploration"
