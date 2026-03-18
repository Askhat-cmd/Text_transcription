import os
from unittest.mock import MagicMock, patch

from utils.reranker import VoyageReranker

DOCS = ["документ первый", "документ второй", "документ третий"]


class TestVoyageReranker:
    def test_returns_indices_list(self):
        with patch.dict(os.environ, {"VOYAGE_API_KEY": "test"}), \
            patch("utils.reranker.voyageai.Client") as mock_client:
            mock_client.return_value.rerank.return_value = MagicMock(
                results=[MagicMock(index=2), MagicMock(index=0), MagicMock(index=1)]
            )
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=3)
        assert indices == [2, 0, 1]

    def test_no_api_key_returns_original_order(self):
        with patch.dict(os.environ, {"VOYAGE_API_KEY": ""}):
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=3)
        assert indices == [0, 1, 2]

    def test_api_exception_returns_original_order(self):
        with patch.dict(os.environ, {"VOYAGE_API_KEY": "test"}), \
            patch("utils.reranker.voyageai.Client") as mock_client:
            mock_client.return_value.rerank.side_effect = Exception("Network error")
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=2)
        assert indices == [0, 1]

    def test_empty_documents_returns_empty(self):
        reranker = VoyageReranker()
        indices = reranker.rerank("запрос", [], top_k=5)
        assert indices == []
