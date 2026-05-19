from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_docs_snapshot_created(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    for name in ("PROJECT_STATE.md", "ROADMAP.md", "PRD_INDEX.md", "DECISIONS.md"):
        (repo_root / "docs" / name).write_text(f"# {name}\n", encoding="utf-8")

    payload = cleanup.create_docs_snapshots(repo_root, write_snapshots=True)
    assert payload["created"] is True
    manifest_path = repo_root / payload["manifest_path"]
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 4
