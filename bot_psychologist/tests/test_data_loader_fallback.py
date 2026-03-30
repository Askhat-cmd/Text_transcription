import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import requests

from bot_agent.config import config
from bot_agent.data_loader import DataLoader, data_loader
from bot_agent.retriever import SimpleRetriever
from api.routes import health_check


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class TestDataLoaderFallback:
    def _build_merged_payload(self, n=25):
        return {
            "schema_version": "bot_data_base_v1.0",
            "blocks": [
                {
                    "id": f"b{i}",
                    "text": f"block {i}",
                    "title": f"title {i}",
                    "summary": "",
                    "sd_level": "GREEN",
                    "sd_confidence": 0.8,
                    "complexity": 0.4,
                    "metadata": {
                        "author": "a",
                        "author_id": "1",
                        "source_title": "src",
                        "language": "ru",
                        "chunk_index": i,
                        "source_type": "book",
                    },
                }
                for i in range(n)
            ],
        }

    def test_api_success_no_fallback(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()

        def fake_get(url, timeout):  # noqa: ARG001
            if url.endswith("/api/registry/"):
                return _FakeResponse([{"source_id": "s1"}], status_code=200)
            if "/api/blocks/" in url:
                return _FakeResponse(
                    {"blocks": [{"id": "b1", "text": "x", "title": "t", "chunk_index": 0}]},
                    status_code=200,
                )
            return _FakeResponse({}, status_code=404)

        with patch("requests.get", side_effect=fake_get):
            result = loader.load()
        assert len(result) == 1
        assert loader._source == "api"

    def test_api_timeout_fallback_to_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        merged_path = tmp_path / "all_blocks_merged.json"
        merged_path.write_text(
            json.dumps(self._build_merged_payload(25), ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "ALL_BLOCKS_MERGED_PATH", str(merged_path), raising=False)

        loader = DataLoader()
        with patch("requests.get", side_effect=requests.exceptions.ReadTimeout("boom")):
            result = loader.load()
        assert len(result) == 25
        assert loader._source == "json_fallback"
        assert bool(getattr(config, "DEGRADED_MODE", False)) is False

    def test_api_timeout_json_missing_degraded(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        monkeypatch.setattr(config, "ALL_BLOCKS_MERGED_PATH", str(Path("Z:/nope/all_blocks_merged.json")), raising=False)
        loader = DataLoader()
        with patch("requests.get", side_effect=requests.exceptions.ReadTimeout("boom")):
            result = loader.load()
        assert result == []
        assert loader._source == "degraded"
        assert bool(getattr(config, "DEGRADED_MODE", False)) is True

    def test_degraded_mode_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(config, "DEGRADED_MODE", True, raising=False)
        monkeypatch.setattr(config, "DATA_SOURCE", "degraded", raising=False)
        retriever = SimpleRetriever()
        result = retriever.retrieve("тест", top_k=5)
        assert result == []

    def test_json_fallback_loads_correct_count(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        merged_path = tmp_path / "all_blocks_merged.json"
        merged_path.write_text(
            json.dumps(self._build_merged_payload(11), ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(config, "ALL_BLOCKS_MERGED_PATH", str(merged_path), raising=False)
        loader = DataLoader()
        with patch("requests.get", side_effect=requests.exceptions.ConnectTimeout("boom")):
            result = loader.load()
        assert len(result) == 11

    def test_health_reports_degraded(self, monkeypatch):
        monkeypatch.setattr(config, "DEGRADED_MODE", True, raising=False)
        monkeypatch.setattr(config, "DATA_SOURCE", "degraded", raising=False)
        monkeypatch.setattr(data_loader, "all_blocks", [], raising=False)
        payload = asyncio.run(health_check())
        assert payload["status"] == "degraded"
        assert payload["bot_data_base_api"] == "unavailable"

    def test_health_reports_json_fallback(self, monkeypatch):
        monkeypatch.setattr(config, "DEGRADED_MODE", False, raising=False)
        monkeypatch.setattr(config, "DATA_SOURCE", "json_fallback", raising=False)
        monkeypatch.setattr(data_loader, "all_blocks", [1] * 25, raising=False)
        payload = asyncio.run(health_check())
        assert payload["status"] == "degraded_fallback"
        assert payload["data_source"] == "json_fallback"
        assert payload["blocks_loaded"] == 25

