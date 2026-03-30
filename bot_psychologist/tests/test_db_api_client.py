import sys
from pathlib import Path
import httpx
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.db_api_client import DBApiClient, DBApiUnavailableError, RetrievedChunk


MOCK_RESPONSE = {
    "chunks": [{
        "chunk_id": "c1",
        "content": "тест",
        "score": 0.9,
        "sd_level": 3,
        "author_id": "auth1",
        "author_name": "Автор",
        "source_type": "youtube",
        "youtube_url": None,
        "start_time": None,
        "end_time": None,
        "block_title": "Блок 1",
        "keywords": ["тест"],
    }],
    "total_found": 1,
    "reranked": True,
    "search_mode": "hybrid",
    "sd_filter_applied": True,
    "query_time_ms": 45,
}


class TestDBApiClient:
    def test_successful_query_returns_chunks(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.return_value = MagicMock(
                status_code=200, json=lambda: MOCK_RESPONSE
            )
            client = DBApiClient()
            result = client.query("осознанность", sd_level=3)
        assert len(result) == 1
        assert isinstance(result[0], RetrievedChunk)
        assert result[0].chunk_id == "c1"

    def test_connect_error_raises_unavailable(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.side_effect = \
                httpx.ConnectError("Connection refused")
            client = DBApiClient()
            with pytest.raises(DBApiUnavailableError) as exc_info:
                client.query("test")
        assert exc_info.value.kind == "connect"
        assert exc_info.value.status_code is None

    def test_timeout_raises_unavailable(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.side_effect = \
                httpx.TimeoutException("Timeout")
            client = DBApiClient()
            with pytest.raises(DBApiUnavailableError) as exc_info:
                client.query("test")
        assert exc_info.value.kind == "timeout"
        assert exc_info.value.status_code is None

    def test_http_status_error_contains_status_code(self):
        request = httpx.Request("POST", "http://localhost:8003/api/query/")
        response = httpx.Response(status_code=503, request=request, text="service unavailable")
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.return_value = response
            client = DBApiClient(retries=1)
            with pytest.raises(DBApiUnavailableError) as exc_info:
                client.query("test")
        assert exc_info.value.kind == "http_status"
        assert exc_info.value.status_code == 503
        assert "503" in str(exc_info.value)

    def test_sd_level_passed_in_payload(self):
        with patch("httpx.Client") as mock_http:
            mock_post = MagicMock(status_code=200, json=lambda: MOCK_RESPONSE)
            mock_http.return_value.__enter__.return_value.post.return_value = mock_post
            client = DBApiClient()
            client.query("тест", sd_level=5)
            call_kwargs = mock_http.return_value.__enter__.return_value.post.call_args
            payload = call_kwargs[1]["json"]
            assert payload["sd_level"] == 5
