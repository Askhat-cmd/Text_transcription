from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_inventory_created() -> None:
    payload = cleanup.collect_artifact_inventory(Path("."))
    assert payload["item_count"] > 0
    assert any(item["path"] == "docs/PROJECT_STATE.md" for item in payload["items"])
