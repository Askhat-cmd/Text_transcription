from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


@pytest.mark.parametrize("status", ["ok"])
def test_controlled_cohort_expansion_botdb_preflight(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    def _fake_probe(_: str) -> dict[str, object]:
        return {}

    def _fake_gate(_: dict[str, object]) -> dict[str, object]:
        return {
            "live_dependency_readiness_passed": True,
            "dashboard_chroma_count": 247,
            "dashboard_chroma_status": status,
            "registry_sources_count": 1,
            "registry_focus_source_id": gate.FOCUS_SOURCE_ID,
            "query_http_200": True,
            "semantic_fallback_used": False,
            "botdb_circuit_open": False,
            "checks": {},
        }

    monkeypatch.setattr(gate.readiness, "probe_live_dependencies", _fake_probe)
    monkeypatch.setattr(gate.readiness, "build_live_dependency_gate", _fake_gate)
    payload = gate.build_botdb_preflight("http://127.0.0.1:8003")
    assert payload["botdb_preflight_passed"] is True
    assert payload["dashboard_chroma_count"] == 247

