from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config import config
from bot_agent.retriever import SimpleRetriever


def test_full_knowledge_access_ignores_legacy_sd_argument(monkeypatch) -> None:
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)

    captured_calls = []

    def _fake_api_retrieve_with_retry(**kwargs):
        captured_calls.append(kwargs)
        return [
            (SimpleNamespace(block_id="b1", title="A"), 0.8),
            (SimpleNamespace(block_id="b2", title="B"), 0.7),
        ]

    monkeypatch.setattr(retriever, "_api_retrieve_with_retry", _fake_api_retrieve_with_retry)

    results = retriever.retrieve(
        query="глубокий вопрос",
        top_k=2,
        sd_level=8,
        author_id=None,
    )

    assert len(results) == 2
    assert len(captured_calls) == 1
    assert "sd_level" not in captured_calls[0]
