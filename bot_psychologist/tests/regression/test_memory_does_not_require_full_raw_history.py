from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_context import compose_memory_context


def test_memory_context_builds_even_without_full_raw_history() -> None:
    bundle = compose_memory_context(
        summary=None,
        summary_updated_at=None,
        total_turns=0,
        snapshot=None,
        recent_turns=[],
    )
    assert bundle.strategy in {
        "missing_summary_snapshot_plus_recent",
        "corrupted_snapshot_recent_dialog",
    }
    assert isinstance(bundle.context_text, str)
