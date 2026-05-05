from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / "bot_psychologist/.env.example"


def _read_env_example() -> str:
    return ENV_EXAMPLE.read_text(encoding="utf-8", errors="ignore")


def test_env_example_sets_multiagent_enabled_true() -> None:
    text = _read_env_example()
    assert "MULTIAGENT_ENABLED=true" in text


def test_env_example_removes_legacy_false_equals_classic_phrase() -> None:
    text = _read_env_example().lower()
    assert "false = классический путь" not in text


def test_env_example_contains_deprecated_compatibility_note() -> None:
    text = _read_env_example().lower()
    assert "deprecated compatibility flag" in text


def test_env_example_agent_defaults_aligned_with_multiagent_runtime() -> None:
    text = _read_env_example()
    assert "STATE_ANALYZER_MODEL=gpt-5-nano" in text
    assert "THREAD_MANAGER_MODEL=gpt-5-nano" in text
    assert "WRITER_MODEL=gpt-5-mini" in text


def test_env_example_contains_thread_manager_reserved_note() -> None:
    text = _read_env_example().lower()
    assert "thread manager" in text
    assert "зарезерв" in text


def test_env_example_contains_legacy_pipeline_disabled_status() -> None:
    text = _read_env_example()
    assert "LEGACY_PIPELINE_ENABLED=false" in text
