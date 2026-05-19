from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_classification_zones_present() -> None:
    inventory = cleanup.collect_artifact_inventory(Path("."))
    classification, _, _ = cleanup.classify_inventory(inventory)
    assert classification["required_zones_present"] is True
    assert "production_runtime" in classification["zone_counts"]
    assert "permanent_quality_eval_regression" in classification["zone_counts"]
