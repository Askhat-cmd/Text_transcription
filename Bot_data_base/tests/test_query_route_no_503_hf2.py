from __future__ import annotations

import asyncio

from api.routes.query import QueryRequest, semantic_query
from api.routes import query as query_route


def test_query_route_returns_200_with_blocks_fallback(monkeypatch):
    monkeypatch.setattr(query_route, "_get_collection", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(query_route, "_fallback_candidates_from_blocks_file", lambda q, limit: [
        {
            "chunk_id": "b1",
            "content": "тестовый контент про поток",
            "metadata": {
                "sd_level": "GREEN",
                "author_id": "a",
                "author": "Автор",
                "source_type": "book",
                "title": "title",
                "governance_schema_version": "v1",
                "governance_chunk_type": "practice",
                "governance_allowed_use": "writer",
                "governance_safety_flags": "safe",
                "governance_lens_family": "lens",
            },
            "distance": None,
        }
    ])
    monkeypatch.setattr(query_route, "apply_retrieval_governance_policy", lambda q, c, top_k: (c[:top_k], {"ok": True}))

    req = QueryRequest(query="что значит быть в потоке", top_k=1, pre_filter_k=10, use_rerank=False, search_mode="hybrid")
    payload = asyncio.run(semantic_query(req))

    assert payload.total_found >= 1
    assert len(payload.chunks) >= 1
