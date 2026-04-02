from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config import config
from bot_agent.retriever import SimpleRetriever


def test_no_hidden_sd_filter_retry(monkeypatch) -> None:
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)

    calls = []

    def _fake_api_retrieve_with_retry(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(retriever, "_api_retrieve_with_retry", _fake_api_retrieve_with_retry)
    monkeypatch.setattr(retriever, "_semantic_fallback", lambda _query, _top_k: [])
    monkeypatch.setattr(retriever, "_tfidf_fallback", lambda _query, _top_k: [])

    results = retriever.retrieve(query="test", top_k=5, sd_level=6)

    assert results == []
    assert len(calls) == 1
    assert "sd_level" not in calls[0]
