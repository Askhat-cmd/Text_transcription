from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v12 import SNAPSHOT_SCHEMA_VERSION, build_snapshot_v12


def test_memory_contract_v12_shape() -> None:
    snapshot = build_snapshot_v12(route="reflect", summary_staleness="fresh")
    assert snapshot["_schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert set(snapshot.keys()) == {
        "nervous_system_state",
        "request_function",
        "dominant_part",
        "active_quadrant",
        "core_theme",
        "last_practice_channel",
        "active_track",
        "insights_log",
        "_schema_version",
        "_updated_at",
        "_last_route",
        "_summary_staleness",
    }
