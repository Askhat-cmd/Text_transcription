from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.fast_detector import detect_sd_level, detect_user_state
from bot_agent.sd_classifier import SDClassificationResult, SDClassifier
from bot_agent.state_classifier import StateClassifier, UserState


def test_detect_sd_fast_obvious_beige() -> None:
    result = detect_sd_level("Мне страшно умереть, не могу дышать, физически плохо")
    assert result is not None
    assert result.label == "BEIGE"
    assert result.confidence >= 0.9


def test_detect_sd_fast_skips_red_for_intellectual_query() -> None:
    result = detect_sd_level("Хочу понять и разобраться, как это работает")
    # Либо нет fast-детекта, либо точно не RED.
    assert result is None or result.label != "RED"


def test_state_classifier_uses_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = StateClassifier()
    monkeypatch.setattr(classifier, "_classify_by_keywords", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(classifier, "_classify_by_llm", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError))

    analysis = classifier.analyze_message("Мне страшно умереть, не могу дышать")
    assert analysis.primary_state == UserState.OVERWHELMED
    assert analysis.confidence >= 0.85
    assert analysis.indicators and analysis.indicators[0].startswith("fast_state:")


def test_sd_classifier_uses_fast_path(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = SDClassifier()
    monkeypatch.setattr(
        classifier,
        "_heuristic_classify",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("heuristic should not run")),
    )
    monkeypatch.setattr(
        classifier,
        "_llm_classify",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("llm should not run")),
    )

    result = classifier.classify("Мне страшно умереть, не могу дышать, физически плохо")
    assert result.primary == "BEIGE"
    assert result.method == "fast"
    assert result.confidence >= 0.85


def test_state_fast_detector_returns_none_for_neutral_text() -> None:
    result = detect_user_state("12345 .....")
    assert result is None


def test_state_classifier_respects_disable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = StateClassifier()
    monkeypatch.setenv("ENABLE_FAST_STATE_DETECTOR", "false")
    monkeypatch.setattr(classifier, "_classify_by_keywords", lambda *_a, **_k: (UserState.CURIOUS, 0.3))
    monkeypatch.setattr(classifier, "_classify_by_llm", lambda *_a, **_k: {})

    analysis = classifier.analyze_message("Мне страшно умереть, не могу дышать")
    assert analysis.primary_state == UserState.CURIOUS


def test_sd_classifier_respects_disable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    classifier = SDClassifier()
    monkeypatch.setenv("ENABLE_FAST_SD_DETECTOR", "false")
    monkeypatch.setattr(
        classifier,
        "_heuristic_classify",
        lambda *_a, **_k: SDClassificationResult(
            primary="ORANGE",
            secondary=None,
            confidence=0.9,
            indicator="heur",
            method="heuristic",
        ),
    )
    result = classifier.classify("Мне страшно умереть, не могу дышать")
    assert result.method == "heuristic"
    assert result.primary == "ORANGE"
