from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_context import resolve_summary_staleness


def test_summary_staleness_fresh() -> None:
    status = resolve_summary_staleness("summary", summary_updated_at=10, total_turns=14, stale_after_turns=8)
    assert status == "fresh"


def test_summary_staleness_stale_when_old() -> None:
    status = resolve_summary_staleness("summary", summary_updated_at=1, total_turns=20, stale_after_turns=8)
    assert status == "stale"


def test_summary_staleness_missing_without_summary() -> None:
    status = resolve_summary_staleness("", summary_updated_at=None, total_turns=3, stale_after_turns=8)
    assert status == "missing"
