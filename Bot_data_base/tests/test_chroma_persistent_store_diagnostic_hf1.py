from __future__ import annotations

from pathlib import Path

from tools import diagnose_chroma_persistent_store_hf1 as diag


class _FailingCollection:
    def count(self):
        raise TypeError("object of type 'int' has no len()")

    def get(self, *args, **kwargs):
        raise TypeError("object of type 'int' has no len()")

    def query(self, *args, **kwargs):
        raise TypeError("object of type 'int' has no len()")


class _FakeManager:
    def __init__(self, **kwargs):
        self._collection = _FailingCollection()

    def probe_collection_health(self):
        return {"status": "unavailable"}

    def _embed_texts(self, texts):
        return [[0.1, 0.2]]

    def source_exists(self, source_id):
        raise TypeError("object of type 'int' has no len()")

    def get_stats(self):
        raise TypeError("object of type 'int' has no len()")


def test_persistent_diagnostic_detects_int_len_fingerprint(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text("storage:\n  chroma_db_path: data/chroma_db\n", encoding="utf-8")

    monkeypatch.setattr(diag, "ChromaManager", _FakeManager)

    payload = diag.run_diagnostic(
        source_prd="PRD-046.1.21-HF1",
        botdb_dir=tmp_path,
        config_path=config,
        expected_source_id="123__кузница_духа",
    )

    assert payload["status"] == "diagnostic_unavailable"
    assert payload["error_count"] >= 1
    assert payload["matches_int_len_fingerprint"] is True
