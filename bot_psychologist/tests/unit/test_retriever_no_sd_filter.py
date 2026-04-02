from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.db_api_client import RetrievedChunk
from bot_agent.retriever import SimpleRetriever


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        content="text",
        score=0.9,
        sd_level=0,
        author_id="a1",
        author_name="author",
        source_type="book",
        youtube_url=None,
        start_time=None,
        end_time=None,
        block_title="Block",
        keywords=[],
    )


def test_api_retrieve_does_not_pass_sd_level_to_db_client(monkeypatch) -> None:
    retriever = SimpleRetriever()
    captured = {}

    def _fake_query(**kwargs):
        captured.update(kwargs)
        return [_chunk()]

    monkeypatch.setattr(retriever.db_client, "query", _fake_query)

    result = retriever._api_retrieve(query="что такое осознанность", top_k=3, author_id="a1")

    assert len(result) == 1
    assert "sd_level" not in captured
    assert captured["query"] == "что такое осознанность"
    assert captured["top_k"] == 3
