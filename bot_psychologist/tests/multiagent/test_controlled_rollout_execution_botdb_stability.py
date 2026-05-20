from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_botdb_stability(monkeypatch) -> None:
    probe = {
        "botdb_live_reachable": True,
        "dashboard_chroma_status": "ok",
        "dashboard_chroma_count": 247,
        "registry_sources_count": 1,
        "semantic_fallback_used": False,
        "botdb_circuit_open": False,
        "checks": {"/api/query/": {"status_code": 200}},
    }
    gate = dict(probe)
    gate["live_dependency_readiness_passed"] = True

    monkeypatch.setattr(execution.readiness, "probe_live_dependencies", lambda _url: probe)
    monkeypatch.setattr(execution.readiness, "build_live_dependency_gate", lambda _probe: gate)

    payload = execution.build_botdb_stability_gate("http://127.0.0.1:8003")
    assert payload["gate_passed"] is True
    assert payload["dashboard_chroma_count"] == 247

