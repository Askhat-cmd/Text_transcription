from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.main import app
from api.routes import registry

client = TestClient(app)


@dataclass
class _SourceObj:
    payload: dict

    @property
    def file_paths(self):
        return self.payload.get("file_paths") or {}

    def to_dict(self) -> dict:
        return dict(self.payload)


class _Registry:
    def __init__(self, source_payload: dict):
        self.source_payload = source_payload
        self.delete_calls = 0

    def get_source(self, source_id: str):
        if source_id == self.source_payload.get("source_id"):
            return _SourceObj(dict(self.source_payload))
        return None

    def delete_source(self, source_id: str):
        self.delete_calls += 1
        return True


class _Chroma:
    def __init__(self):
        self.delete_calls = 0

    def source_exists(self, source_id: str) -> bool:
        return True

    def delete_source(self, source_id: str) -> int:
        self.delete_calls += 1
        return 1


class _Runner:
    def __init__(self, source_payload: dict):
        self.registry = _Registry(source_payload)
        self.chroma_manager = _Chroma()
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_delete_blocked_source_does_not_mutate_registry_or_chroma(monkeypatch) -> None:
    source = {
        "source_id": "blocked_source",
        "source_type": "book",
        "title": "book",
        "status": "done",
        "blocks_count": 10,
        "file_paths": {},
    }
    runner = _Runner(source)

    monkeypatch.setattr(registry, "_get_runner", lambda: runner)
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda r: {"123__кузница_духа"})

    response = client.delete("/api/registry/blocked_source")
    assert response.status_code == 409
    assert runner.registry.delete_calls == 0
    assert runner.chroma_manager.delete_calls == 0


def test_focus_source_delete_does_not_mutate_registry_or_chroma(monkeypatch) -> None:
    source = {
        "source_id": "123__кузница_духа",
        "source_type": "book",
        "title": "Кузница Духа",
        "status": "done",
        "blocks_count": 247,
        "file_paths": {},
    }
    runner = _Runner(source)

    monkeypatch.setattr(registry, "_get_runner", lambda: runner)
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda r: {"123__кузница_духа"})

    response = client.delete("/api/registry/123__кузница_духа")
    assert response.status_code == 409
    assert runner.registry.delete_calls == 0
    assert runner.chroma_manager.delete_calls == 0
