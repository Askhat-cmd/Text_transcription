from __future__ import annotations

import json
from pathlib import Path

from tools import reindex_focus_source_chroma_controlled as controlled


class _FakeManager:
    def __init__(self):
        self.reset_called = False

    def reset_collection(self):
        self.reset_called = True

    def add_blocks(self, blocks):
        return len(blocks)


def test_focus_recovery_blocked_when_non_focus_blocks_present(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        "storage:\n  chroma_db_path: data/chroma_db\n  collection_name: test\nembedding:\n  model: test\n",
        encoding="utf-8",
    )

    blocks = {
        "blocks": [
            {"id": "1", "source": "book:123__кузница_духа", "text": "a", "metadata": {}},
            {"id": "2", "source": "book:other_source", "text": "b", "metadata": {}},
        ]
    }
    blocks_path = tmp_path / "all_blocks_merged.json"
    blocks_path.write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")

    fake_manager = _FakeManager()

    def _fake_probe_collection(**kwargs):
        return {
            "health": {"status": "ok"},
            "collection_count": 0,
            "source_ids": [],
            "manager": fake_manager,
        }

    monkeypatch.setattr(controlled, "_probe_collection", _fake_probe_collection)
    monkeypatch.setattr(controlled, "_to_universal_block", lambda row: row)

    payload = controlled.run_controlled_reindex(
        source_prd="PRD-046.1.21-HF1",
        botdb_dir=tmp_path,
        config_path=config,
        blocks_path=blocks_path,
        expected_source_id="123__кузница_духа",
        expected_blocks=2,
        backup_root=tmp_path / "backup",
        confirm=True,
    )

    result = payload["result"]
    assert result["status"] == "failed"
    assert result["reindex_performed"] is False
    assert "source_ids_not_focus_only" in result["preflight_issues"]
