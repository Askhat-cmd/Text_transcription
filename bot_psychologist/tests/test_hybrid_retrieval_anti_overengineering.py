from __future__ import annotations

from pathlib import Path


COMPOSER_PATH = (
    Path(__file__).resolve().parents[1]
    / "bot_agent"
    / "multiagent"
    / "contextual_retrieval_query_composer.py"
)


def test_contextual_retrieval_composer_has_no_forbidden_domain_hardcoding() -> None:
    source = COMPOSER_PATH.read_text(encoding="utf-8-sig").lower()

    for marker in (
        "кузница духа",
        "автоматизм",
        "защитный механизм",
        "самореализация",
    ):
        assert marker not in source
