import json
from pathlib import Path

from tools import kb_quality_audit


def test_chroma_readiness_handles_api_unavailable(tmp_path: Path, monkeypatch) -> None:
    all_blocks_path = tmp_path / "all_blocks_merged.json"
    all_blocks_path.write_text(json.dumps({"blocks": [{"id": "1"}]}), encoding="utf-8")

    def fake_http(_method: str, _url: str, payload=None, timeout=7.0):  # noqa: ARG001
        return {"ok": False, "status_code": None, "body": None, "error": "connection refused"}

    monkeypatch.setattr(kb_quality_audit, "_http_json", fake_http)

    result = kb_quality_audit.probe_chroma_readiness(
        api_base_url="http://127.0.0.1:8003",
        config={"storage": {"chroma_db_path": "data/chroma_db", "collection_name": "kb"}},
        all_blocks_path=all_blocks_path,
        registry_records=[],
    )
    assert result["api_status"]["status_code"] is None
    assert result["all_blocks_exists"] is True
    assert result["local_blocks_count"] == 1
    assert "collection_dimension_detected" in result
    assert "embedding_probe_dimension" in result


def test_chroma_readiness_handles_query_503_and_count_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    all_blocks_path = tmp_path / "all_blocks_merged.json"
    all_blocks_path.write_text(
        json.dumps({"blocks": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}), encoding="utf-8"
    )

    def fake_http(_method: str, url: str, payload=None, timeout=7.0):  # noqa: ARG001
        if url.endswith("/api/query/"):
            return {"ok": False, "status_code": 503, "body": {"detail": "ChromaDB unavailable"}}
        return {"ok": True, "status_code": 200, "body": {}}

    class FakeCollection:
        def count(self) -> int:
            return 1

    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

        def list_collections(self):
            class C:
                name = "kb"

            return [C()]

        def get_collection(self, name: str):  # noqa: ARG002
            return FakeCollection()

    class FakeSettings:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

    monkeypatch.setattr(kb_quality_audit, "_http_json", fake_http)
    fake_chromadb = type("FakeChromaDb", (), {"PersistentClient": FakeClient})
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)
    monkeypatch.setitem(
        __import__("sys").modules,
        "chromadb.config",
        type("FakeChromaCfg", (), {"Settings": FakeSettings}),
    )

    result = kb_quality_audit.probe_chroma_readiness(
        api_base_url="http://127.0.0.1:8003",
        config={
            "storage": {"chroma_db_path": "data/chroma_db", "collection_name": "kb"},
            "embedding": {"model": "intfloat/multilingual-e5-large"},
        },
        all_blocks_path=all_blocks_path,
        registry_records=[
            {
                "error_message": "Collection expecting embedding with dimension of 1024, got 3",
            }
        ],
    )
    assert result["api_query"]["status_code"] == 503
    assert result["collection_exists"] is True
    assert result["collection_count"] == 1
    assert result["local_blocks_count"] == 3
    assert result["safe_reset_or_reindex_recommended"] is True
    assert result["possible_embedding_dimension_mismatch"] is True
    assert "collection_count_error" in result
    assert "collection_dimension_detection_reason" in result
