from __future__ import annotations

import logging

from bot_agent.state_classifier import (
    StateAnalysis,
    StateClassifier,
    UserState,
    VALID_NSS,
    VALID_REQUEST_FUNCTIONS,
)


def _analysis(state: UserState, confidence: float = 0.81) -> StateAnalysis:
    return StateAnalysis(
        primary_state=state,
        confidence=confidence,
        secondary_states=[],
        indicators=[],
        emotional_tone="neutral",
        depth="surface",
        recommendations=["ok"],
    )


def test_runtime_result_uses_neo_vocab() -> None:
    classifier = StateClassifier()
    result = classifier._to_runtime_result(_analysis(UserState.CURIOUS), "как это работает?")
    assert result.nervous_system_state in VALID_NSS
    assert result.request_function in VALID_REQUEST_FUNCTIONS
    assert 0.0 <= result.confidence <= 1.0


def test_runtime_request_function_solution_detected() -> None:
    classifier = StateClassifier()
    result = classifier._to_runtime_result(
        _analysis(UserState.COMMITTED),
        "Скажи, что делать дальше и дай шаги",
    )
    assert result.request_function == "solution"


def test_state_classifier_logs_neo_axes_without_legacy_terms(caplog) -> None:
    classifier = StateClassifier()
    with caplog.at_level(logging.INFO, logger="bot_agent.state_classifier"):
        classifier._classify_by_keywords = lambda _msg: (UserState.CURIOUS, 0.83)  # type: ignore[method-assign]
        classifier._classify_by_llm = lambda *_args, **_kwargs: {}  # type: ignore[method-assign]
        classifier.analyze_message("Что такое самонаблюдение?")

    info_messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
    assert any("STATE nss=" in message for message in info_messages)
    lowered = "\n".join(info_messages).lower()
    assert "curious" not in lowered
    assert "confused" not in lowered
    assert "committed" not in lowered
