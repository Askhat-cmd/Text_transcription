from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.memory_v11 import SNAPSHOT_SCHEMA_VERSION, build_snapshot_v11


def test_memory_contract_v11_shape() -> None:
    snapshot = build_snapshot_v11(route="reflect", summary_staleness="fresh")
    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert set(snapshot.keys()) == {
        "schema_version",
        "updated_at",
        "diagnostics",
        "routing",
        "engagement",
        "meta",
    }
    assert "interaction_mode" in snapshot["diagnostics"]
    assert "nervous_system_state" in snapshot["diagnostics"]
    assert "request_function" in snapshot["diagnostics"]
    assert "core_theme" in snapshot["diagnostics"]
    assert "last_route" in snapshot["routing"]
    assert "summary_staleness" in snapshot["meta"]
