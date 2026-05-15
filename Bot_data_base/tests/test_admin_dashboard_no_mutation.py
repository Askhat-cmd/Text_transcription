from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
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


class _NoMutationRegistry:
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
            )
        ]

    def list_all(self):
        return list(self._sources)

    def get_statistics(self) -> dict:
        return {"total_sources": 1, "total_blocks": 247, "sd_distribution": {}, "sources_by_type": {"book": 1}}

    def add_source(self, *_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not mutate registry")

    def update_status(self, *_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not mutate registry")

    def delete_source(self, *_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not mutate registry")


class _NoMutationChroma:
    def get_stats(self) -> dict:
        return {"total": 247}

    def add_blocks(self, *_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not mutate chroma")

    def delete_source(self, *_args, **_kwargs):
        raise AssertionError("dashboard endpoint must not mutate chroma")


class _NoMutationRunner:
    def __init__(self) -> None:
        self.registry = _NoMutationRegistry()
        self.chroma_manager = _NoMutationChroma()
        self.json_exporter = SimpleNamespace(base_dir="unused")


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_dashboard_no_mutation(monkeypatch, tmp_path: Path) -> None:
    marker = tmp_path / "mutation_sentinel.txt"
    marker.write_text("sentinel", encoding="utf-8")
    before = _hash(marker)

    monkeypatch.setattr(dashboard, "_get_runner", lambda: _NoMutationRunner())
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
    assert _hash(marker) == before
