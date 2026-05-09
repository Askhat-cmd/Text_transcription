from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot_agent.config import config
from bot_agent.db_api_client import DBApiUnavailableError
from bot_agent.retriever import SimpleRetriever


def _http_503_chromadb_error() -> DBApiUnavailableError:
    return DBApiUnavailableError(
        'HTTP 503 from Bot_data_base: {"detail":"ChromaDB unavailable"}',
        kind="http_status",
        status_code=503,
    )


def test_first_503_opens_circuit(monkeypatch):
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_ENABLED", True, raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS", 60.0, raising=False)
    monkeypatch.setattr(config, "BOT_DB_FAST_FAIL_ON_503", True, raising=False)
    with patch.object(SimpleRetriever, "_api_retrieve_with_retry", side_effect=_http_503_chromadb_error()) as api:
        with patch("bot_agent.retriever.feature_flags.enabled", return_value=True):
            with patch.object(SimpleRetriever, "_semantic_fallback", return_value=[(MagicMock(), 0.8)]) as semantic:
                result = retriever.retrieve("test", top_k=1)
    assert api.call_count == 1
    assert semantic.call_count == 1
    assert len(result) == 1
    assert retriever._is_circuit_open() is True


def test_second_call_within_ttl_skips_api(monkeypatch):
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_ENABLED", True, raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS", 60.0, raising=False)
    monkeypatch.setattr(config, "BOT_DB_FAST_FAIL_ON_503", True, raising=False)

    with patch.object(SimpleRetriever, "_api_retrieve_with_retry", side_effect=_http_503_chromadb_error()) as api:
        with patch("bot_agent.retriever.feature_flags.enabled", return_value=True):
            with patch.object(SimpleRetriever, "_semantic_fallback", return_value=[(MagicMock(), 0.8)]):
                _ = retriever.retrieve("first", top_k=1)
                _ = retriever.retrieve("second", top_k=1)
    assert api.call_count == 1


def test_after_ttl_api_is_tried_again(monkeypatch):
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_ENABLED", True, raising=False)
    monkeypatch.setattr(config, "BOT_DB_FAST_FAIL_ON_503", True, raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS", 1.0, raising=False)
    # Manually expire circuit.
    retriever._bot_db_circuit_open_until = retriever._now() - 1.0

    with patch.object(SimpleRetriever, "_api_retrieve_with_retry", return_value=[(MagicMock(), 0.9)]) as api:
        _ = retriever.retrieve("test", top_k=1)
    assert api.call_count == 1


def test_circuit_breaker_can_be_disabled(monkeypatch):
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "KNOWLEDGE_SOURCE", "api", raising=False)
    monkeypatch.setattr(config, "BOT_DB_CIRCUIT_BREAKER_ENABLED", False, raising=False)
    monkeypatch.setattr(config, "BOT_DB_FAST_FAIL_ON_503", True, raising=False)

    with patch.object(SimpleRetriever, "_api_retrieve_with_retry", side_effect=_http_503_chromadb_error()) as api:
        with patch("bot_agent.retriever.feature_flags.enabled", return_value=True):
            with patch.object(SimpleRetriever, "_semantic_fallback", return_value=[]):
                with patch.object(SimpleRetriever, "_tfidf_fallback", return_value=[(MagicMock(), 0.3)]):
                    _ = retriever.retrieve("first", top_k=1)
                    _ = retriever.retrieve("second", top_k=1)
    assert api.call_count == 2


def test_fast_fail_503_skips_retry(monkeypatch):
    retriever = SimpleRetriever()
    monkeypatch.setattr(config, "BOT_DB_FAST_FAIL_ON_503", True, raising=False)
    with patch.object(SimpleRetriever, "_api_retrieve", side_effect=_http_503_chromadb_error()) as api:
        try:
            retriever._api_retrieve_with_retry(query="x", top_k=1)
        except DBApiUnavailableError:
            pass
    assert api.call_count == 1
