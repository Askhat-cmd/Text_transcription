import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.config import config
from bot_agent.data_loader import Block
from bot_agent.db_api_client import DBApiUnavailableError
from bot_agent.retriever import SimpleRetriever


class _DummyProvider:
    def __init__(self, query_vec):
        self._query_vec = list(query_vec)

    def embed_query(self, _text):
        return list(self._query_vec)

    def model_name(self):
        return "dummy"


class TestRetrieverFallback:
    def test_uses_api_when_available(self):
        with patch("bot_agent.db_api_client.DBApiClient.query") as mock_api:
            mock_api.return_value = [
                MagicMock(
                    score=0.9,
                    chunk_id="c1",
                    content="x",
                    sd_level=3,
                    author_id="",
                    author_name="",
                    source_type="book",
                    youtube_url=None,
                    start_time=None,
                    end_time=None,
                    block_title=None,
                    keywords=[],
                )
            ]
            retriever = SimpleRetriever()
            result = retriever.retrieve("осознанность", sd_level=3)
        mock_api.assert_called_once()
        assert len(result) == 1

    def test_falls_back_to_tfidf_when_api_down(self):
        with patch(
            "bot_agent.db_api_client.DBApiClient.query",
            side_effect=DBApiUnavailableError("down"),
        ):
            with patch.object(SimpleRetriever, "_semantic_fallback", return_value=[]) as mock_semantic:
                with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[MagicMock()]) as mock_tfidf:
                    retriever = SimpleRetriever()
                    result = retriever.retrieve("осознанность")
        mock_semantic.assert_called_once()
        mock_tfidf.assert_called_once()
        assert len(result) == 1

    def test_retries_without_sd_when_zero_results(self):
        call_count = 0

        def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("sd_level", 0) > 0:
                return []
            return [
                MagicMock(
                    score=0.5,
                    chunk_id="c2",
                    content="x",
                    sd_level=2,
                    author_id="",
                    author_name="",
                    source_type="book",
                    youtube_url=None,
                    start_time=None,
                    end_time=None,
                    block_title=None,
                    keywords=[],
                )
            ]

        with patch("bot_agent.db_api_client.DBApiClient.query", side_effect=mock_query):
            retriever = SimpleRetriever()
            result = retriever.retrieve("практики", sd_level=7)
        assert call_count == 2
        assert len(result) == 1

    def test_uses_semantic_fallback_before_tfidf(self, monkeypatch):
        retriever = SimpleRetriever()
        retriever._is_built = True
        retriever.blocks = [
            Block(block_id="b1", title="t1", content="alpha"),
            Block(block_id="b2", title="t2", content="beta"),
        ]
        retriever.semantic_matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        retriever._semantic_ready = True
        retriever._embedding_provider = _DummyProvider([1.0, 0.0])

        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        with patch.object(SimpleRetriever, "_api_retrieve", side_effect=DBApiUnavailableError("down")):
            with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[]) as tfidf:
                results = retriever.retrieve("query", top_k=1)

        tfidf.assert_not_called()
        assert len(results) == 1
        assert results[0][0].block_id == "b1"

    def test_uses_tfidf_when_semantic_fallback_empty(self, monkeypatch):
        retriever = SimpleRetriever()
        retriever._is_built = True
        retriever.blocks = [Block(block_id="b1", title="t1", content="alpha")]
        retriever.semantic_matrix = np.array([[0.0, 1.0]], dtype=np.float32)
        retriever._semantic_ready = True
        retriever._embedding_provider = _DummyProvider([1.0, 0.0])

        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        with patch.object(SimpleRetriever, "_api_retrieve", side_effect=DBApiUnavailableError("down")):
            with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[MagicMock()]) as tfidf:
                results = retriever.retrieve("query", top_k=1)

        tfidf.assert_called_once()
        assert len(results) == 1

    def test_semantic_fallback_can_be_disabled_by_feature_flag(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EMBEDDING_PROVIDER", "false")
        with patch("bot_agent.db_api_client.DBApiClient.query", side_effect=DBApiUnavailableError("down")):
            with patch.object(SimpleRetriever, "_semantic_fallback", return_value=[MagicMock()]) as semantic:
                with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[MagicMock()]) as tfidf:
                    retriever = SimpleRetriever()
                    results = retriever.retrieve("query", top_k=1)

        semantic.assert_not_called()
        tfidf.assert_called_once()
        assert len(results) == 1
