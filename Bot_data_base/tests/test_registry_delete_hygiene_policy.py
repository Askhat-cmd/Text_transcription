from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
        self.deleted = False

    def get_source(self, source_id: str):
        if source_id == self.source_payload.get("source_id"):
            return _SourceObj(dict(self.source_payload))
        return None

    def delete_source(self, source_id: str):
        if source_id == self.source_payload.get("source_id"):
            self.deleted = True
            return True
        return False


class _Runner:
    def __init__(self, source_payload: dict, *, chroma_exists: bool = False):
        self.registry = _Registry(source_payload)
        self.chroma_manager = SimpleNamespace(
            source_exists=lambda source_id: chroma_exists,
            delete_source=lambda source_id: 0,
        )
        self.json_exporter = SimpleNamespace(base_dir=str(Path.cwd() / "tmp_processed"))


def test_focus_source_delete_forbidden(monkeypatch) -> None:
    source = {
        "source_id": "123__кузница_духа",
        "source_type": "book",
        "title": "Кузница Духа",
        "status": "done",
        "blocks_count": 247,
        "file_paths": {},
    }
    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner(source))
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda runner: {"123__кузница_духа"})

    response = client.delete("/api/registry/123__кузница_духа")
    assert response.status_code == 409
    assert "Основной источник базы" in response.json().get("detail", "")


def test_zero_block_archived_delete_allowed(monkeypatch, tmp_path: Path) -> None:
    upload = tmp_path / "tmp_upload.txt"
    export = tmp_path / "tmp_blocks.json"
    upload.write_text("x", encoding="utf-8")
    export.write_text("{}", encoding="utf-8")

    source = {
        "source_id": "test_zero",
        "source_type": "book",
        "title": "test",
        "status": "archived",
        "blocks_count": 0,
        "file_paths": {"upload": str(upload), "json": str(export)},
    }

    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner(source))
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda runner: {"123__кузница_духа"})
    monkeypatch.setattr(registry, "_create_registry_snapshot", lambda runner, reason: "snapshot.json")

    response = client.delete("/api/registry/test_zero")
    assert response.status_code == 200
    payload = response.json()
    assert payload["removed"] is True
    assert payload["snapshot_path"] == "snapshot.json"


def test_one_block_test_like_delete_allowed_when_not_in_prod_and_not_in_chroma(monkeypatch) -> None:
    source = {
        "source_id": "test_one",
        "source_type": "book",
        "title": "book",
        "status": "failed",
        "blocks_count": 1,
        "file_paths": {},
    }
    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner(source, chroma_exists=False))
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda runner: {"123__кузница_духа"})
    monkeypatch.setattr(registry, "_create_registry_snapshot", lambda runner, reason: "snapshot.json")

    response = client.delete("/api/registry/test_one")
    assert response.status_code == 200
    assert response.json()["policy_code"] == "registry_only_blocks_test_like"
