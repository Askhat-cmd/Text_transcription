from __future__ import annotations

import logging

import bot_agent.diagnostics_classifier as diag_module
from bot_agent.diagnostics_classifier import DiagnosticsClassifier
from bot_agent.state_classifier import StateClassifierResult


def test_validate_no_legacy_warning_for_valid_neo_terms(caplog) -> None:
    classifier = DiagnosticsClassifier()
    payload = StateClassifierResult(
        nervous_system_state="window",
        request_function="understand",
        confidence=0.87,
        raw_label="curious",
    )

    with caplog.at_level(logging.WARNING, logger="bot_agent.diagnostics_classifier"):
        result = classifier.validate(payload)

    assert result.nervous_system_state == "window"
    assert result.request_function == "understand"
    assert not [r for r in caplog.records if "legacy term" in r.message.lower()]


def test_validate_invalid_terms_fallback_with_error(caplog) -> None:
    classifier = DiagnosticsClassifier()
    payload = StateClassifierResult(
        nervous_system_state="bad_value",
        request_function="bad_fn",
        confidence=0.4,
        raw_label="bad",
    )

    with caplog.at_level(logging.ERROR, logger="bot_agent.diagnostics_classifier"):
        result = classifier.validate(payload)

    assert result.nervous_system_state == "window"
    assert result.request_function == "understand"
    error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
    assert any("invalid nss" in message.lower() for message in error_messages)
    assert any("invalid fn" in message.lower() for message in error_messages)


def test_legacy_mapper_removed_from_diagnostics_module() -> None:
    assert not hasattr(diag_module, "LEGACY_STATE_MAP")
