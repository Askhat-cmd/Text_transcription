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
                    "source_id": "123__кузница_духа",
                    "source_type": "book",
                    "title": "Кузница Духа",
                    "status": "done",
                    "author": "Author",
                    "language": "ru",
                    "blocks_count": 247,
                    "added_at": "2026-05-15T10:00:00+00:00",
                }
            ),
            _Source(
                {
                    "source_id": "tmp_zero",
                    "source_type": "book",
                    "title": "test",
                    "status": "archived",
                    "author": "",
                    "language": "ru",
                    "blocks_count": 0,
                    "added_at": "2026-05-15T10:01:00+00:00",
                }
            ),
        ]

    def get_statistics(self) -> dict:
        return {"total_sources": 2, "total_blocks": 247, "sources_by_type": {"book": 2}}


class _Runner:
    def __init__(self) -> None:
        self.registry = _Registry()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 247}, source_exists=lambda _: False)
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_registry_runtime_contract(monkeypatch) -> None:
    html = (registry._repo_root() / "Bot_data_base" / "web_ui" / "registry.html").read_text(encoding="utf-8")
    js = (registry._repo_root() / "Bot_data_base" / "web_ui" / "static" / "registry.js").read_text(encoding="utf-8")

    assert "/static/registry.js?v=046_0_9_run1_hf3" in html
    assert "id=\"registry-errors\"" in html
    assert "encodeURIComponent(id)" in js

    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner())
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda _runner: {"123__кузница_духа"})

    response = client.get("/api/registry/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2

    focus_row = next(row for row in payload["sources"] if row["source_id"] == "123__кузница_духа")
    assert focus_row["blocks_count"] == 247
    assert focus_row["delete_policy"]["state"] == "protected"
