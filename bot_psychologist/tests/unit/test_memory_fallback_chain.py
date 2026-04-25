from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_context import compose_memory_context
from bot_agent.memory_v12 import build_snapshot_v12


@dataclass
class _Turn:
    user_input: str
    bot_response: str


def _turns() -> list[_Turn]:
    return [
        _Turn(user_input="first", bot_response="resp1"),
        _Turn(user_input="second", bot_response="resp2"),
        _Turn(user_input="third", bot_response="resp3"),
        _Turn(user_input="fourth", bot_response="resp4"),
    ]


def test_memory_fallback_chain_fresh_summary_prefers_summary() -> None:
    snapshot = build_snapshot_v12(
        diagnostics={
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "core",
        },
        route="reflect",
        summary_staleness="fresh",
    )
    bundle = compose_memory_context(
        summary="fresh summary",
        summary_updated_at=4,
        total_turns=5,
        snapshot=snapshot,
        recent_turns=_turns(),
    )
    assert bundle.strategy == "fresh_summary_small_window"
    assert bundle.summary_used is True


def test_memory_fallback_chain_missing_summary_uses_snapshot_and_recent() -> None:
    snapshot = build_snapshot_v12(route="reflect", summary_staleness="missing")
    bundle = compose_memory_context(
        summary=None,
        summary_updated_at=None,
        total_turns=4,
        snapshot=snapshot,
        recent_turns=_turns(),
    )
    assert bundle.strategy == "missing_summary_snapshot_plus_recent"
    assert bundle.summary_used is False
    assert bundle.snapshot_used is True
    assert bundle.recent_window_used is True


def test_memory_fallback_chain_corrupted_snapshot_ignores_broken_fields() -> None:
    broken_snapshot = {"_schema_version": "0.0", "nervous_system_state": "window"}
    bundle = compose_memory_context(
        summary="old summary",
        summary_updated_at=1,
        total_turns=12,
        snapshot=broken_snapshot,
        recent_turns=_turns(),
    )
    assert bundle.strategy == "corrupted_snapshot_recent_dialog"
    assert bundle.snapshot_used is False
