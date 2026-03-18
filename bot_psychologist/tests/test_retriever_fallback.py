import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.retriever import SimpleRetriever
from bot_agent.db_api_client import DBApiUnavailableError


class TestRetrieverFallback:
    def test_uses_api_when_available(self):
        with patch("bot_agent.db_api_client.DBApiClient.query") as mock_api:
            mock_api.return_value = [MagicMock(score=0.9, chunk_id="c1", content="x",
                                               sd_level=3, author_id="", author_name="",
                                               source_type="book", youtube_url=None,
                                               start_time=None, end_time=None,
                                               block_title=None, keywords=[])]
            retriever = SimpleRetriever()
            result = retriever.retrieve("осознанность", sd_level=3)
        mock_api.assert_called_once()
        assert len(result) == 1

    def test_falls_back_to_tfidf_when_api_down(self):
        with patch("bot_agent.db_api_client.DBApiClient.query",
                   side_effect=DBApiUnavailableError("down")):
            with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[MagicMock()]) as mock_tfidf:
                retriever = SimpleRetriever()
                result = retriever.retrieve("осознанность")
        mock_tfidf.assert_called_once()
        assert len(result) == 1

    def test_retries_without_sd_when_zero_results(self):
        call_count = 0

        def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("sd_level", 0) > 0:
                return []
            return [MagicMock(score=0.5, chunk_id="c2", content="x",
                              sd_level=2, author_id="", author_name="",
                              source_type="book", youtube_url=None,
                              start_time=None, end_time=None,
                              block_title=None, keywords=[])]

        with patch("bot_agent.db_api_client.DBApiClient.query", side_effect=mock_query):
            retriever = SimpleRetriever()
            result = retriever.retrieve("практики", sd_level=7)
        assert call_count == 2
        assert len(result) == 1
