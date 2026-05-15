from __future__ import annotations

from pathlib import Path

from tools import controlled_candidate_apply


class _FakeManager:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        self.count = 229
        self.reset_called = False
        self.add_called = False

    def probe_collection_health(self):
        return {"collection_count": self.count, "embedding_model_name": "fake"}

    def reset_collection(self):
        self.reset_called = True
        self.count = 0

    def add_blocks(self, blocks):
        self.add_called = True
        self.count = len(blocks)
        return len(blocks)


def test_chroma_reindex_reports_expected_count(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(controlled_candidate_apply, "_load_config", lambda _path: {"storage": {"chroma_db_path": "data/chroma_db", "collection_name": "test"}, "embedding": {"model": "m"}})
    fake = _FakeManager()
    monkeypatch.setattr(controlled_candidate_apply, "ChromaManager", lambda *args, **kwargs: fake)
    monkeypatch.setattr(controlled_candidate_apply, "_to_universal_block", lambda raw: raw)

    blocks = [{"id": "b1", "source": "book:123__кузница_духа", "text": "x"}, {"id": "b2", "source": "book:123__кузница_духа", "text": "y"}]
    result = controlled_candidate_apply.run_chroma_reindex(
        config_path=tmp_path / "config.yaml",
        blocks=blocks,
        source_id="123__кузница_духа",
    )
    assert fake.reset_called is True
    assert fake.add_called is True
    assert result["indexed_blocks_count"] == 2
    assert result["chroma_count_after"] == 2
    assert result["status"] == "passed"
