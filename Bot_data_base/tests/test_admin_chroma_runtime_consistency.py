from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.main import app
from api.routes import dashboard, registry

client = TestClient(app)


@dataclass
class _Source:
    payload: dict

    def to_dict(self) -> dict:
        return dict(self.payload)


class _RegistryImpl:
    def list_all(self):
        return [
            _Source(
                {
                    "source_id": "123__кузница_духа",
                    "source_type": "book",
                    "title": "Кузница Духа",
                    "status": "done",
                    "blocks_count": 247,
                    "processed_at": "2026-05-15T11:00:00+00:00",
                }
            )
        ]

    def get_statistics(self) -> dict:
        return {"total_sources": 1, "total_blocks": 247, "sources_by_type": {"book": 1}}


class _Runner:
    def __init__(self) -> None:
        self.registry = _RegistryImpl()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 247}, source_exists=lambda _: False)
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_admin_chroma_runtime_consistency(monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "_get_runner", lambda: _Runner())
    monkeypatch.setattr(registry, "_get_runner", lambda: _Runner())
    monkeypatch.setattr(
        dashboard,
        "_load_blocks_payload",
        lambda _runner: {
            "blocks": [
                {
                    "source": "book:123__кузница_духа",
                    "metadata": {"governance": {"allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]}},
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
    monkeypatch.setattr(registry, "_load_production_source_ids", lambda _runner: {"123__кузница_духа"})

    dashboard_payload = client.get("/api/dashboard").json()
    registry_stats = client.get("/api/registry/stats").json()

    assert dashboard_payload["chroma"]["status"] == "ok"
    assert dashboard_payload["chroma"]["count"] == 247
    assert registry_stats["chroma_total"] == 247
    assert dashboard_payload["blocks"]["production_total"] == 247
