from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class _DummyRunner:
    def __init__(self):
        self.chroma_manager = SimpleNamespace(_embed_texts=lambda texts: [[0.1, 0.2, 0.3] for _ in texts])
        self.registry = SimpleNamespace(get_source=lambda _source_id: None)


@contextmanager
def _patched_query_runtime(mock_collection):
    with patch("api.routes.query._get_collection", return_value=mock_collection), patch(
        "api.routes.query._get_runner", return_value=_DummyRunner()
    ):
        yield


def _mock_results():
    return {
        "documents": [["text 1", "text 2"]],
        "metadatas": [[
            {"sd_level": "GREEN", "author_id": "a1", "author": "Author", "source_type": "book"},
            {"sd_level": "BLUE", "author_id": "a1", "author": "Author", "source_type": "book"},
        ]],
        "distances": [[0.1, 0.2]],
        "ids": [["chunk1", "chunk2"]],
    }


def test_query_accepts_sd_level_but_ignores_filter(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    mock_collection = MagicMock()
    mock_collection.query.return_value = _mock_results()

    with _patched_query_runtime(mock_collection):
        response = client.post(
            "/api/query/",
            json={"query": "практика", "sd_level": 6, "author_id": "a1", "use_rerank": False},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sd_filter_applied"] is False
    assert payload["debug"]["legacy_sd_deprecated"] is True
    assert payload["debug"]["sd_level_ignored"] is True
    where_arg = mock_collection.query.call_args.kwargs.get("where")
    assert where_arg == {"author_id": {"$eq": "a1"}}
