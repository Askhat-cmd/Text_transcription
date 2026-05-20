from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_live_dependency_gate_logic() -> None:
    probe = {
        "status_endpoint_ok": True,
        "registry_endpoint_ok": True,
        "dashboard_endpoint_ok": True,
        "focus_source_present": True,
        "focus_source_id": "123__кузница_духа",
        "registry_source_count": 1,
        "blocks_count": 247,
        "chroma_count": 247,
        "query_path_ready": True,
        "semantic_fallback_used": False,
        "botdb_circuit_open": False,
        "checks": {"/": {"ok": True}},
    }
    payload = gate.build_live_dependency_gate(probe, strict=True, allow_offline_skip=False)
    assert payload["botdb_live_status"] == "passed"
    assert payload["live_dependency_gate_passed"] is True

