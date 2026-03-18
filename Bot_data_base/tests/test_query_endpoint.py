from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _mock_results():
    return {
        "documents": [["текст 1", "текст 2"]],
        "metadatas": [[
            {
                "sd_level": "GREEN",
                "author_id": "sarsekanov",
                "author": "Сарсенов Саламат",
                "source_type": "book",
                "title": "Блок 1",
                "keywords": ["тест"],
            },
            {
                "sd_level": "BLUE",
                "author_id": "sarsekanov",
                "author": "Сарсенов Саламат",
                "source_type": "book",
                "title": "Блок 2",
                "keywords": ["тест2"],
            },
        ]],
        "distances": [[0.2, 0.4]],
        "ids": [["chunk_001", "chunk_002"]],
    }


class TestQueryEndpointBasic:
    def test_returns_200_on_valid_request(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "что такое осознанность"})
        assert response.status_code == 200

    def test_response_schema_valid(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "осознанность", "top_k": 3})
        data = response.json()
        assert "chunks" in data
        assert "total_found" in data
        assert "reranked" in data
        assert "search_mode" in data
        assert "query_time_ms" in data

    def test_empty_query_returns_422(self):
        response = client.post("/api/query/", json={"query": ""})
        assert response.status_code == 422

    def test_top_k_respected(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "практики", "top_k": 1})
        data = response.json()
        assert len(data["chunks"]) <= 1

    def test_returns_chunks_structure(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "осознанность"})
        if response.json()["chunks"]:
            chunk = response.json()["chunks"][0]
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "score" in chunk
            assert "sd_level" in chunk
            assert "author_id" in chunk


class TestQueryEndpointSDFilter:
    def test_sd_level_0_returns_all_levels(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "практики", "sd_level": 0})
        assert response.json()["sd_filter_applied"] is False

    def test_sd_level_4_applies_filter(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "практики", "sd_level": 4})
        assert response.status_code == 200

    def test_fallback_when_no_sd_chunks(self):
        mock_collection = MagicMock()
        mock_collection.query.side_effect = [
            {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]},
            _mock_results(),
        ]
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "редкий запрос xyz", "sd_level": 8})
        assert response.status_code == 200
        assert response.json()["sd_filter_applied"] is False


class TestQueryEndpointAuthorFilter:
    def test_author_filter_applied(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "осознанность", "author_id": "sarsekanov"})
        for chunk in response.json()["chunks"]:
            assert chunk["author_id"] == "sarsekanov"

    def test_unknown_author_returns_empty(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
        with patch("api.routes.query._get_collection", return_value=mock_collection):
            response = client.post("/api/query/", json={"query": "осознанность", "author_id": "nonexistent_author_xyz"})
        assert response.status_code == 200
        assert response.json()["total_found"] == 0


class TestQueryEndpointRerank:
    def test_use_rerank_false_skips_voyage(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection), \
            patch("utils.reranker.VoyageReranker.rerank") as mock_rerank:
            client.post("/api/query/", json={"query": "тест", "use_rerank": False})
            mock_rerank.assert_not_called()

    def test_voyage_failure_graceful_degradation(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = _mock_results()
        with patch("api.routes.query._get_collection", return_value=mock_collection), \
            patch("utils.reranker.VoyageReranker.rerank", side_effect=Exception("API Error")):
            response = client.post("/api/query/", json={"query": "практики", "use_rerank": True})
        assert response.status_code == 200
