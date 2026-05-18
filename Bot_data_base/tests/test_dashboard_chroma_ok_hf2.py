from __future__ import annotations

from api.routes import dashboard


class _FakeRegistry:
    def list_all(self):
        class _Row:
            def __init__(self, row):
                self._row = row

            def to_dict(self):
                return dict(self._row)

        return [_Row({"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247, "source_type": "book", "title": "Кузница"})]

    def get_statistics(self):
        return {"total_sources": 1, "total_blocks": 247}


class _FakeRunner:
    def __init__(self):
        self.registry = _FakeRegistry()


def test_dashboard_uses_runtime_health(monkeypatch):
    monkeypatch.setattr(dashboard, "_get_runner", lambda: _FakeRunner())
    monkeypatch.setattr(dashboard, "get_chroma_runtime_health", lambda _: {"status": "ok", "count": 247, "source_ids": ["123__кузница_духа"]})
    monkeypatch.setattr(dashboard, "_load_blocks_payload", lambda runner: {"blocks": []})
    monkeypatch.setattr(dashboard, "_governance_summary", lambda blocks: {"readiness": "ready", "governance_present_rate": 1.0, "allowed_use_present_rate": 1.0, "safety_flags_present_rate": 1.0, "legacy_sd_active": False})
    monkeypatch.setattr(dashboard, "_load_enrichment_summary", lambda: ({"provider_status": "ok", "items_completed": 0, "validation_errors_count": 0, "validation_warnings_count": 0, "review_queue_items_count": 0, "p0": 0, "p1": 0, "p2": 0, "production_apply_performed": False}, []))

    payload = dashboard._build_dashboard_summary()

    assert payload["chroma"]["status"] == "ok"
    assert payload["chroma"]["count"] == 247
