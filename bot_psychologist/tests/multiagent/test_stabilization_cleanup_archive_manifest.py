from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_archive_manifest_non_destructive() -> None:
    inventory = cleanup.collect_artifact_inventory(Path("."))
    _, archive_manifest, cleanup_manifest = cleanup.classify_inventory(inventory)
    assert archive_manifest["archive_mode"] == "manifest_only"
    assert archive_manifest["physical_files_deleted"] == 0
    assert cleanup_manifest["physical_deletion_performed"] is False
    assert all(item["delete_now"] is False for item in cleanup_manifest["items"])
