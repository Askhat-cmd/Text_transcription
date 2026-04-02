from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.practice_selector import practice_selector


def test_golden_hyper_discharge_prefers_body() -> None:
    selection = practice_selector.select(
        route="regulate",
        nervous_system_state="hyper",
        request_function="discharge",
        core_theme="острая тревога",
    )
    assert selection.primary is not None
    assert selection.primary.entry.channel == "body"


def test_golden_hypo_contact_prefers_soft_body_or_contact() -> None:
    selection = practice_selector.select(
        route="contact_hold",
        nervous_system_state="hypo",
        request_function="contact",
        core_theme="пустота",
    )
    assert selection.primary is not None
    assert selection.primary.entry.channel in {"body", "reflection"}


def test_golden_window_understand_prefers_thinking_or_action() -> None:
    selection = practice_selector.select(
        route="reflect",
        nervous_system_state="window",
        request_function="understand",
        core_theme="избегание",
    )
    assert selection.primary is not None
    assert selection.primary.entry.channel in {"thinking", "action", "reflection"}


def test_golden_rotation_and_alternatives_limit() -> None:
    selection = practice_selector.select(
        route="reflect",
        nervous_system_state="window",
        request_function="explore",
        core_theme="конфликт",
        last_practice_channel="body",
        max_alternatives=2,
    )
    assert selection.primary is not None
    assert len(selection.alternatives) <= 2
    if selection.alternatives:
        assert selection.alternatives[0].entry.id != selection.primary.entry.id

