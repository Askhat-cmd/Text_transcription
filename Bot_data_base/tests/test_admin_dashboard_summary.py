from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.main import app
from api.routes import dashboard

client = TestClient(app)


@dataclass
class _Source:
    payload: dict

    def to_dict(self) -> dict:
        return dict(self.payload)


class _DummyRegistry:
    def __init__(self) -> None:
        self._sources = [
            _Source(
                {
                    "source_id": "123__кузница_духа",
                    "source_type": "book",
                    "title": "Кузница Духа",
                    "status": "done",
                    "blocks_count": 247,
                    "processed_at": "2026-05-15T05:40:00+00:00",
                }
            ),
            _Source(
                {
                    "source_id": "test_source",
                    "source_type": "book",
                    "title": "book",
                    "status": "archived",
                    "blocks_count": 0,
                    "processed_at": "2026-05-10T00:00:00+00:00",
                }
            ),
        ]

    def list_all(self):
        return list(self._sources)

    def get_statistics(self) -> dict:
        return {"total_sources": 2, "total_blocks": 247, "sd_distribution": {}, "sources_by_type": {"book": 2}}


class _DummyRunner:
    def __init__(self) -> None:
        self.registry = _DummyRegistry()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 247})
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_dashboard_summary_contract(monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "_get_runner", lambda: _DummyRunner())
    monkeypatch.setattr(
        dashboard,
        "_load_blocks_payload",
        lambda runner: {
            "blocks": [
                {
                    "source": "book:123__кузница_духа",
                    "metadata": {
                        "governance": {
                            "allowed_use": ["writer_context"],
                            "safety_flags": ["not_for_direct_quote"],
                        }
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        dashboard,
        "_load_enrichment_summary",
        lambda: (
            {
                "provider_status": "called",
                "items_completed": 247,
                "validation_errors_count": 0,
                "validation_warnings_count": 0,
                "review_queue_items_count": 87,
                "p0": 0,
                "p1": 1,
                "p2": 86,
                "production_apply_performed": False,
            },
            [],
        ),
    )

    response = client.get("/api/dashboard/")
    assert response.status_code == 200

    data = response.json()
    assert data["schema_version"] == "botdb_dashboard_summary_v1"
    assert data["status"] == "ok"
    assert data["sources"]["total"] == 2
    assert data["blocks"]["production_total"] == 247
    assert data["chroma"]["count"] == 247
    assert data["governance"]["readiness"] == "ready"
    assert data["enrichment"]["provider_status"] == "called"
    assert data["enrichment"]["review_queue_items_count"] == 87
    assert data["recent_sources"][0]["source_id"] == "123__кузница_духа"
    assert data["recent_sources"][0]["protected"] is True
    assert data["warnings"] == []
