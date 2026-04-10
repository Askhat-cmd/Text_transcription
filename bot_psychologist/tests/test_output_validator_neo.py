from __future__ import annotations

import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.output_validator import output_validator


NEO_ANSWER = (
    "Понял твое состояние и то, как тревога сжимает внимание перед важным разговором. "
    "Обычно это смесь защиты и усталости нервной системы, а не признак слабости. "
    "Если хочешь, дальше можно разобрать конкретный триггер и выбрать шаг на сегодня."
)


def test_thin_body_detects_only_one_very_short_sentence() -> None:
    result = output_validator.validate(
        "Тревога мешает.",
        route="inform",
        mode="PRESENCE",
        query="объясни тревогу",
    )
    assert result.valid is False
    assert "underfilled_inform_answer" in result.errors
    assert result.needs_regeneration is True


def test_thin_body_does_not_trigger_for_two_short_sentences() -> None:
    result = output_validator.validate(
        "Тревога мешает. Это частая реакция.",
        route="inform",
        mode="PRESENCE",
        query="объясни тревогу",
    )
    assert "underfilled_inform_answer" not in result.errors
    assert result.valid is True


def test_explicit_short_query_skips_thin_body_rule() -> None:
    result = output_validator.validate(
        "Тревога мешает.",
        route="inform",
        mode="PRESENCE",
        query="кратко: что делать",
    )
    assert "underfilled_inform_answer" not in result.errors
    assert result.valid is True


def test_preserve_structure_true_keeps_markdown() -> None:
    raw = "### Шаги\n```text\n1. Дыши\n```\nСначала замедлись и верни опору."
    result = output_validator.validate(
        raw,
        route="reflect",
        mode="PRESENCE",
        query="что делать при тревоге",
        preserve_structure=True,
    )
    assert "```" in result.text
    assert "markdown_structure_preserved" in result.warnings
    assert result.repair_applied is False


def test_preserve_structure_false_strips_markdown() -> None:
    raw = "### Шаги\n```text\n1. Дыши\n```\nСначала замедлись и верни опору."
    result = output_validator.validate(
        raw,
        route="reflect",
        mode="PRESENCE",
        query="что делать при тревоге",
    )
    assert "```" not in result.text
    assert "markdown_leakage" in result.warnings
    assert result.repair_applied is True


def test_validate_signature_has_preserve_structure_default_false() -> None:
    sig = inspect.signature(output_validator.validate)
    assert "preserve_structure" in sig.parameters
    assert sig.parameters["preserve_structure"].default is False


def test_regeneration_hint_mentions_preserving_neo_structure() -> None:
    hint = output_validator.build_regeneration_hint(
        ["underfilled_inform_answer"],
        route="inform",
        mode="CLARIFICATION",
        query="чем отличается тревога от страха",
    ).lower()
    assert "сохрани полный объём ответа" in hint


def test_neo_routes_validate_with_preserve_structure() -> None:
    neo_routes = ["reflect", "inform", "presence", "intervention", "safe_override"]
    for route in neo_routes:
        result = output_validator.validate(
            NEO_ANSWER,
            route=route,
            mode="PRESENCE",
            query="что происходит при тревоге",
            preserve_structure=True,
        )
        assert result.valid, f"route={route} errors={result.errors}"


def test_empty_output_is_invalid() -> None:
    result = output_validator.validate("", route="reflect", mode="PRESENCE", query="вопрос")
    assert result.valid is False
    assert result.needs_regeneration is True
    assert "empty_output" in result.errors


def test_needs_regeneration_matches_error_presence() -> None:
    ok = output_validator.validate(
        NEO_ANSWER,
        route="reflect",
        mode="PRESENCE",
        query="вопрос",
        preserve_structure=True,
    )
    bad = output_validator.validate(
        "Коротко.",
        route="inform",
        mode="PRESENCE",
        query="объясни тревогу",
    )
    assert ok.needs_regeneration == bool(ok.errors)
    assert bad.needs_regeneration == bool(bad.errors)
