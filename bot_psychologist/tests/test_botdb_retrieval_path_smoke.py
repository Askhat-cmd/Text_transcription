from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SMOKE_PATH = PROJECT_ROOT / "tools" / "botdb_retrieval_path_smoke.py"
spec = importlib.util.spec_from_file_location("botdb_retrieval_path_smoke", SMOKE_PATH)
assert spec and spec.loader
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class _DummyBlock:
    def __init__(self, idx: int) -> None:
        self.block_id = f"b{idx}"
        self.title = f"title {idx}"
        self.source_type = "book"
        self.content = "safe content"
        self.governance = {
            "chunk_type": "lens",
            "allowed_use": ["writer_context"],
            "safety_flags": ["not_for_direct_quote"],
            "lens_family": ["shame"],
        }


class _FakeRetriever:
    def __init__(self) -> None:
        self._calls = 0

    def retrieve(self, query: str, top_k: int = 4):  # noqa: ARG002
        self._calls += 1
        if self._calls == 2:
            return []
        return [(_DummyBlock(self._calls), 0.8)]

    def get_last_retrieval_debug(self):
        if self._calls == 2:
            return {"retrieval_source_attempted": "api", "retrieval_source_used": "tfidf_fallback", "bot_db_circuit_open": False}
        return {"retrieval_source_attempted": "api", "retrieval_source_used": "api", "bot_db_circuit_open": False}


def test_run_smoke_detects_mixed_api_and_fallback(monkeypatch) -> None:
    monkeypatch.setattr(smoke, "SimpleRetriever", _FakeRetriever)
    payload = smoke.run_smoke(api_base_url="http://127.0.0.1:8003", top_k=3)
    assert payload["botdb_api_attempted"] is True
    assert payload["fallback_used"] is True
    assert payload["retrieval_source"] in {"botdb_api", "fallback_or_mixed"}
    assert len(payload["queries"]) == 3
