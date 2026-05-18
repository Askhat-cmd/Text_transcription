from __future__ import annotations

import asyncio

from api.routes import registry as registry_route


class _FakeRegistry:
    def get_statistics(self):
        return {"total_sources": 2, "total_blocks": 247, "sources_by_type": {"book": 1}}

    def list_all(self):
        class _Row:
            def __init__(self, row):
                self._row = row

            def to_dict(self):
                return dict(self._row)

        return [_Row({"source_id": "123__кузница_духа", "blocks_count": 247, "source_type": "book", "status": "done"})]


class _FakeChroma:
    def get_stats(self):
        raise TypeError("object of type 'int' has no len()")


class _FakeRunner:
    def __init__(self):
        self.registry = _FakeRegistry()
        self.chroma_manager = _FakeChroma()
        self.json_exporter = type("Exporter", (), {"base_dir": "."})()


def test_registry_stats_chroma_exception_returns_200_contract(monkeypatch):
    monkeypatch.setattr(registry_route, "_get_runner", lambda: _FakeRunner())

    payload = asyncio.run(registry_route.get_stats())

    assert payload["chroma_total"] == 0
    assert payload["chroma_status"] == "unavailable"
    assert payload["chroma_error_code"] == "chroma_stats_unavailable"
    assert payload["total_blocks"] == 247
    assert any("degraded mode" in item for item in payload.get("warnings", []))
    assert all("Traceback" not in item for item in payload.get("warnings", []))
