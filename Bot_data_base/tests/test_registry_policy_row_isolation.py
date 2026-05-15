from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.main import app
from api.routes import registry

client = TestClient(app)


@dataclass
class _Source:
    payload: dict

    def to_dict(self) -> dict:
        return dict(self.payload)


class _Registry:
    def list_all(self):
        return [
            _Source(
                {
                    "source_id": "broken_row",
                    "source_type": "book",
                    "title": "broken",
                    "status": "failed",
                    "blocks_count": 1,
                }
            ),
            _Source(
                {
                    "source_id": "ok_row",
                    "source_type": "book",
                    "title": "ok",
                    "status": "archived",
                    "blocks_count": 0,
                }
            ),
        ]


class _Runner:
    def __init__(self) -> None:
        self.registry = _Registry()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 0}, source_exists=lambda _: False)
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_registry_row_policy_isolation(monkeypatch) -> None:
    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner())
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda _runner: set())

    original = registry._resolve_delete_policy

    def _patched(source_row, *, production_source_ids, runner):
        if source_row.get("source_id") == "broken_row":
            raise RuntimeError("policy exploded")
        return original(source_row, production_source_ids=production_source_ids, runner=runner)

    monkeypatch.setattr(registry, "_resolve_delete_policy", _patched)

    response = client.get("/api/registry/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2

    broken = next(row for row in payload["sources"] if row["source_id"] == "broken_row")
    assert broken["delete_policy"]["state"] == "unavailable"
    assert "Ошибка политики" in broken["delete_policy"]["reason"]

    ok_row = next(row for row in payload["sources"] if row["source_id"] == "ok_row")
    assert ok_row["delete_policy"]["state"] == "delete"

    warnings = payload.get("warnings", [])
    assert any("row_policy_error:broken_row" in item for item in warnings)
