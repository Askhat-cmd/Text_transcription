from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.db_api_client import DBApiClient


def test_retrieval_contract_v101_payload_has_no_sd_level() -> None:
    with patch("httpx.Client") as mock_http:
        mock_post = MagicMock(status_code=200, json=lambda: {"chunks": []})
        mock_http.return_value.__enter__.return_value.post.return_value = mock_post

        client = DBApiClient()
        client.query(
            query="что происходит",
            sd_level=7,
            top_k=4,
            author_id="author-1",
            use_rerank=True,
            search_mode="hybrid",
        )

        call_kwargs = mock_http.return_value.__enter__.return_value.post.call_args[1]
        payload = call_kwargs["json"]

    assert set(payload.keys()) == {"query", "top_k", "author_id", "use_rerank", "search_mode"}
    assert payload["query"] == "что происходит"
    assert payload["top_k"] == 4
    assert payload["author_id"] == "author-1"
    assert payload["use_rerank"] is True
    assert payload["search_mode"] == "hybrid"
