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
        self.registry = SimpleNamespace(get_source=lambda source_id: None)


@contextmanager
def _patched_query_runtime(mock_collection):
    with patch("api.routes.query._get_collection", return_value=mock_collection), patch(
        "api.routes.query._get_runner", return_value=_DummyRunner()
    ):
        yield


def _results_for_policy_filter() -> dict:
    return {
        "documents": [["internal block", "regular block"]],
        "metadatas": [[
            {
                "sd_level": "GREEN",
                "author_id": "a1",
                "author": "Author",
                "source_type": "book",
                "title": "Internal Safety",
                "keywords": ["k1"],
                "governance_schema_version": "governance_v1",
                "governance_chunk_type": "safety",
                "governance_allowed_use": "internal_only,safety_protocol",
                "governance_safety_flags": "not_for_direct_quote,source_style_not_user_facing",
                "governance_lens_family": "safety",
                "governance_not_for_direct_quote": "true",
                "governance_source_style_not_user_facing": "true",
            },
            {
                "sd_level": "GREEN",
                "author_id": "a2",
                "author": "Author2",
                "source_type": "book",
                "title": "Regular",
                "keywords": ["k2"],
                "governance_schema_version": "governance_v1",
                "governance_chunk_type": "lens",
                "governance_allowed_use": "writer_context,diagnostic_lens",
                "governance_safety_flags": "not_for_direct_quote",
                "governance_lens_family": "self_criticism",
                "governance_not_for_direct_quote": "true",
                "governance_source_style_not_user_facing": "false",
            },
        ]],
        "distances": [[0.1, 0.2]],
        "ids": [["chunk_internal", "chunk_regular"]],
    }


def test_non_safety_query_filters_internal_only() -> None:
    mock_collection = MagicMock()
    mock_collection.query.return_value = _results_for_policy_filter()

    with _patched_query_runtime(mock_collection):
        response = client.post(
            "/api/query/",
            json={"query": "если я не лучший, я будто никто", "top_k": 5, "use_rerank": False},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chunks"], payload
    for chunk in payload["chunks"]:
        allowed_use = chunk.get("governance", {}).get("allowed_use", [])
        assert "internal_only" not in [str(item).lower() for item in allowed_use]


def test_safety_query_keeps_internal_only() -> None:
    mock_collection = MagicMock()
    mock_collection.query.return_value = _results_for_policy_filter()

    with _patched_query_runtime(mock_collection):
        response = client.post(
            "/api/query/",
            json={"query": "мне очень плохо и я на грани", "top_k": 5, "use_rerank": False},
        )

    assert response.status_code == 200
    payload = response.json()
    allowed_values = [
        item.lower()
        for chunk in payload.get("chunks", [])
        for item in chunk.get("governance", {}).get("allowed_use", [])
    ]
    assert "internal_only" in allowed_values

