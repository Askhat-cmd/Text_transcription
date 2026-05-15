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
    def list_all(self):
        return [
            _Source(
                {
                    "source_id": "123__кузница_духа",
                    "source_type": "book",
                    "title": "Кузница Духа",
                    "status": "done",
                    "blocks_count": 247,
                    "processed_at": "2026-05-15T05:40:00+00:00",
                }
            )
        ]

    def get_statistics(self) -> dict:
        return {"total_sources": 1, "total_blocks": 247, "sd_distribution": {}, "sources_by_type": {"book": 1}}


class _DummyRunner:
    def __init__(self) -> None:
        self.registry = _DummyRegistry()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 247})
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_dashboard_enrichment_unknown_is_visible(monkeypatch) -> None:
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
                "provider_status": "unknown",
                "items_completed": 0,
                "validation_errors_count": 0,
                "validation_warnings_count": 0,
                "review_queue_items_count": 0,
                "p0": 0,
                "p1": 0,
                "p2": 0,
                "production_apply_performed": False,
            },
            ["enrichment_scorecard_missing", "review_queue_artifact_missing"],
        ),
    )

    response = client.get("/api/dashboard/")
    assert response.status_code == 200

    data = response.json()
    assert data["sources"]["total"] == 1
    assert data["blocks"]["production_total"] == 247
    assert data["chroma"]["count"] == 247
    assert data["enrichment"]["provider_status"] == "unknown"
    assert "enrichment_state_unknown" in data["warnings"]
    assert "enrichment_scorecard_missing" in data["warnings"]
    assert "review_queue_artifact_missing" in data["warnings"]
