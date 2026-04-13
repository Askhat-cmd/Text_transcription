from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v11 import build_snapshot_v11, compose_memory_context_v11


@dataclass
class _Turn:
    user_input: str
    bot_response: str


def test_context_continuity_between_sessions_uses_summary_plus_recent_window() -> None:
    previous_summary = "Пользователь исследует паттерн избегания ответственности."
    snapshot = build_snapshot_v11(
        diagnostics={
            "interaction_mode": "coaching",
            "nervous_system_state": "window",
            "request_function": "explore",
            "core_theme": "избегание ответственности",
        },
        route="reflect",
        summary_staleness="fresh",
    )
    turns = [
        _Turn(user_input="я снова откладываю важные дела", bot_response="давай разберем шаг за шагом"),
        _Turn(user_input="хочу изменить это", bot_response="выделим один небольшой шаг"),
    ]
    bundle = compose_memory_context_v11(
        summary=previous_summary,
        summary_updated_at=4,
        total_turns=5,
        snapshot=snapshot,
        recent_turns=turns,
    )
    assert bundle.summary_used is True
    assert bundle.snapshot_used is False
    assert previous_summary in bundle.context_text
