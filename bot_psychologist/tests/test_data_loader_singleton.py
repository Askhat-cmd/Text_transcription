import threading
import time
from unittest.mock import patch

from bot_agent.config import config
from bot_agent.data_loader import DataLoader


class TestDataLoaderSingleton:
    def test_load_called_once_on_double_init(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()
        with patch.object(loader, "_load_from_api", return_value=None) as mock_api:
            loader.load()
            loader.load()
            assert mock_api.call_count == 1

    def test_cache_hit_returns_same_data(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()

        def _load_once():
            loader.all_blocks = [{"id": "b1", "text": "test"}]
            loader._source = "api"

        with patch.object(loader, "_load_from_api", side_effect=_load_once):
            result1 = loader.load()
            result2 = loader.load()
            assert result1 is result2
            assert len(result1) == 1

    def test_reload_forces_refetch(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()
        with patch.object(loader, "_load_from_api", return_value=None) as mock_api:
            loader.load()
            loader.reload()
            assert mock_api.call_count == 2

    def test_thread_safety(self, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()
        call_count = {"n": 0}

        def _slow_load():
            call_count["n"] += 1
            time.sleep(0.05)
            loader.all_blocks = [{"id": "b1"}]
            loader._source = "api"

        with patch.object(loader, "_load_from_api", side_effect=_slow_load):
            threads = [threading.Thread(target=loader.load) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        assert call_count["n"] == 1

    def test_cache_hit_log_present(self, monkeypatch, caplog):
        monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
        loader = DataLoader()
        with patch.object(loader, "_load_from_api", return_value=None):
            loader.load()
            loader.load()
        cache_logs = [r for r in caplog.records if "[DATA_LOADER] cache_hit" in r.message]
        assert len(cache_logs) >= 1

