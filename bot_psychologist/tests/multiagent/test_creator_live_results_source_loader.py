from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_source_loader_blocks_missing() -> None:
    missing_dir = Path("Z:/definitely_missing_path_046_1_35")
    preflight = gate.preflight_source_artifacts(missing_dir, missing_dir)
    manifest = preflight["source_artifacts_manifest"]
    assert preflight["ok"] is False
    assert manifest["source_artifacts_gate"] == "blocked"
    assert manifest["missing_artifact_count"] > 0

