from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_docs_compaction_passed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "PROJECT_STATE.md").write_text("old project state\n", encoding="utf-8")
    (docs_dir / "ROADMAP.md").write_text("old roadmap\n", encoding="utf-8")
    (docs_dir / "PRD_INDEX.md").write_text("# PRD Index\n", encoding="utf-8")
    (docs_dir / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")

    snapshot = cleanup.create_docs_snapshots(repo_root, write_snapshots=True)
    report = cleanup.compact_docs(repo_root, compact=True, snapshot_proof=snapshot)
    assert report["docs_compaction_passed"] is True
    assert report["runtime_map_created"] is True
    assert report["eval_harness_map_created"] is True
    decisions_text = (docs_dir / "DECISIONS.md").read_text(encoding="utf-8")
    assert "ADR-049" in decisions_text
