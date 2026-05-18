from __future__ import annotations

from pathlib import Path

from storage import chroma_runtime_health as health


class _FakeCollection:
    def __init__(self):
        self._rows = [{"source_id": "123__кузница_духа"}, {"source_id": "123__кузница_духа"}]

    def count(self):
        return 2

    def get(self, **kwargs):  # noqa: ARG002
        return {"metadatas": self._rows}


class _FakeClient:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass

    def get_or_create_collection(self, name):  # noqa: ARG002
        return _FakeCollection()


def test_chroma_runtime_health_reports_ok(monkeypatch, tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "storage:\n  chroma_db_path: data/chroma_db\n  collection_name: bot_knowledge_base\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(health.chromadb, "PersistentClient", _FakeClient)

    payload = health.get_chroma_runtime_health(str(cfg))

    assert payload["status"] == "ok"
    assert payload["count"] == 2
    assert payload["source_ids"] == ["123__кузница_духа"]
    assert payload["count_by_source_id"]["123__кузница_духа"] == 2
