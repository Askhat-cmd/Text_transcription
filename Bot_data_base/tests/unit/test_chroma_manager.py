import numpy as np

from models.universal_block import UniversalBlock
from storage.chroma_manager import ChromaManager


class DummyModel:
    def encode(self, texts, convert_to_numpy=True):
        return np.zeros((len(texts), 3), dtype=float)


def test_add_and_count(tmp_path, monkeypatch):
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())
    manager = ChromaManager(":memory:", "test_col")
    blocks = [
        UniversalBlock(text=f"Блок {i}", sd_level="GREEN", source_id="src1", source_type="book")
        for i in range(3)
    ]
    added = manager.add_blocks(blocks)
    assert added == 3


def test_delete_source(tmp_path, monkeypatch):
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())
    manager = ChromaManager(":memory:", "test_col")
    blocks = [
        UniversalBlock(text="test", source_id="src1", source_type="book", sd_level="GREEN")
    ]
    manager.add_blocks(blocks)
    deleted = manager.delete_source("src1")
    assert deleted >= 1
    assert not manager.source_exists("src1")


def test_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(ChromaManager, "_init_embedding_model", lambda self: DummyModel())
    manager = ChromaManager(":memory:", "test_col")
    stats = manager.get_stats()
    assert "total" in stats
    assert "by_sd_level" in stats
