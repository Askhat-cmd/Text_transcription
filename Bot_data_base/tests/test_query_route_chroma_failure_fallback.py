from __future__ import annotations

import asyncio

from api.routes import query as query_route
from api.routes.query import QueryRequest, semantic_query


class _MalformedCollection:
    def query(self, **kwargs):
        return {
            "documents": ["контент о нейросталкинге"],
            "metadatas": [1],  # malformed row (legacy failure: len(int))
            "distances": [0.12],
            "ids": ["chunk-1"],
        }


class _DummyRunner:
    class _DummyChroma:
        @staticmethod
        def _embed_texts(texts):
            return [[0.1, 0.2, 0.3]]

    chroma_manager = _DummyChroma()



def test_query_route_handles_malformed_chroma_rows_without_len_int_failure(monkeypatch):
    monkeypatch.setattr(query_route, "_get_collection", lambda: _MalformedCollection())
    monkeypatch.setattr(query_route, "_get_runner", lambda: _DummyRunner())
    monkeypatch.setattr(
        query_route,
        "apply_retrieval_governance_policy",
        lambda q, c, top_k: (c[:top_k], {"ok": True}),
    )

    req = QueryRequest(
        query="что такое нейросталкинг",
        top_k=1,
        pre_filter_k=5,
        use_rerank=False,
        search_mode="hybrid",
    )
    payload = asyncio.run(semantic_query(req))

    assert payload.total_found == 1
    assert payload.chunks[0].chunk_id == "chunk-1"
    assert "нейросталкинге" in payload.chunks[0].content
