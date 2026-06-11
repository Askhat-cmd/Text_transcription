from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from api.main import app
from bot_agent.config import config
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)
    with TestClient(app, base_url="http://localhost") as client:
        yield client


def test_runtime_effective_exposes_hybrid_retrieval_planner_contract(admin_client):
    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    planner = payload["hybrid_retrieval_planner"]
    assert planner["enabled"] is True
    assert planner["version"] == "hybrid_retrieval_planner_v1_r1"
    assert planner["mode"] in {"off", "shadow", "apply"}
    assert planner["default_safe_mode"] == "shadow"
    assert planner["metadata_only"] is True
    assert planner["query_before_rag_supported"] is True
    assert planner["writer_final_author_preserved"] is True
    assert planner["domain_specific_hardcoding_allowed"] is False
