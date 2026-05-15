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


class _Registry:
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
        return {"total_sources": 1, "total_blocks": 248, "sd_distribution": {}, "sources_by_type": {"book": 1}}


class _Runner:
    def __init__(self) -> None:
        self.registry = _Registry()
        self.chroma_manager = SimpleNamespace(get_stats=lambda: {"total": 247})
        self.json_exporter = SimpleNamespace(base_dir="unused")


def test_dashboard_runtime_contract_static_and_api(monkeypatch) -> None:
    html = (dashboard._repo_root() / "Bot_data_base" / "web_ui" / "index.html").read_text(encoding="utf-8")
    js = (dashboard._repo_root() / "Bot_data_base" / "web_ui" / "static" / "app.js").read_text(encoding="utf-8")

    assert "/static/app.js?v=046_0_9_run1_hf2" in html
    assert "loadDashboard" in js
    assert "fetchJSON('/api/dashboard')" in js

    monkeypatch.setattr(dashboard, "_get_runner", lambda: _Runner())
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

    no_slash = client.get("/api/dashboard")
    with_slash = client.get("/api/dashboard/")

    assert no_slash.status_code == 200
    assert with_slash.status_code == 200
    assert no_slash.json()["schema_version"] == "botdb_dashboard_summary_v1"
    assert no_slash.json()["blocks"]["production_total"] == 247
    assert no_slash.json()["blocks"]["registry_total"] == 248
