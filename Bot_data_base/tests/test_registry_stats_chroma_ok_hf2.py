from __future__ import annotations

import asyncio
import json
from pathlib import Path

from api.routes import registry as registry_route


class _FakeRegistry:
    def get_statistics(self):
        return {"total_sources": 1, "total_blocks": 247, "sources_by_type": {"book": 1}}

    def list_all(self):
        class _Row:
            def __init__(self, row):
                self._row = row

            def to_dict(self):
                return dict(self._row)

        return [_Row({"source_id": "123__кузница_духа", "blocks_count": 247, "source_type": "book", "status": "done"})]


class _FakeRunner:
    def __init__(self, tmp_path: Path):
        self.registry = _FakeRegistry()
        self.chroma_manager = object()
        self.json_exporter = type("Exporter", (), {"base_dir": str(tmp_path)})()


def test_registry_stats_reports_chroma_ok(monkeypatch, tmp_path: Path):
    (tmp_path / "all_blocks_merged.json").write_text(json.dumps({"blocks": [{"source": "book:123__кузница_духа"}]}), encoding="utf-8")
    monkeypatch.setattr(registry_route, "_get_runner", lambda: _FakeRunner(tmp_path))
    monkeypatch.setattr(registry_route, "get_chroma_runtime_health", lambda _: {"status": "ok", "count": 247})

    payload = asyncio.run(registry_route.get_stats())

    assert payload["chroma_status"] == "ok"
    assert payload["chroma_total"] == 247
    assert payload["chroma_error_code"] is None
