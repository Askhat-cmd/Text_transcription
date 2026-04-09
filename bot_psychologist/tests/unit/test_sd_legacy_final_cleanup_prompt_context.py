from __future__ import annotations

import inspect

import bot_agent.answer_adaptive as adaptive
from bot_agent.state_classifier import StateAnalysis, UserState


def _state() -> StateAnalysis:
    return StateAnalysis(
        primary_state=UserState.CURIOUS,
        confidence=0.82,
        secondary_states=[],
        indicators=[],
        emotional_tone="neutral",
        depth="surface",
        recommendations=["Respond clearly."],
    )


def test_state_context_uses_neo_axes_without_sd_lines() -> None:
    context = adaptive._build_state_context(
        _state(),
        mode_prompt="MODE",
        nervous_system_state="window",
        request_function="understand",
    )
    assert "nervous_system_state: window" in context
    assert "request_function: understand" in context
    assert "Уровень развития (СД)" not in context
    assert "SD-оверлей" not in context
    assert "SD-" not in context


def test_answer_adaptive_has_no_sd_runtime_disabled_log_line() -> None:
    source = inspect.getsource(adaptive)
    assert "SD runtime disabled in Neo v11 pipeline" not in source
